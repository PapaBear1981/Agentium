"""
Agent Service - FastAPI application for multi-agent orchestration.

This service provides HTTP endpoints for agent management, task processing,
and system monitoring.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import structlog

from agent import AgentOrchestrator
from models.agents import TaskRequest, TaskResponse, AgentStatus
from models.voice import VoiceConfig

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Global orchestrator instance
orchestrator: Optional[AgentOrchestrator] = None
startup_time = time.time()

# Request/Response models
class TaskProcessRequest(BaseModel):
    content: str
    session_id: str
    context: Optional[Dict] = None
    priority: str = "medium"

class TaskProcessResponse(BaseModel):
    task_id: str
    result: str
    success: bool
    agent_id: str
    tokens_used: int = 0
    cost: float = 0.0
    processing_time_ms: int = 0
    metadata: Optional[Dict] = None

class VoiceProcessRequest(BaseModel):
    operation: str  # 'stt' or 'tts'
    data: str  # audio data (base64) or text
    session_id: str
    config: Optional[Dict] = None

class VoiceProcessResponse(BaseModel):
    success: bool
    result: Optional[Dict] = None
    error: Optional[str] = None

class SystemStatusResponse(BaseModel):
    status: str
    uptime_seconds: int
    agents: Dict[str, Dict]
    active_sessions: int
    total_tasks_processed: int
    supporting_systems: Dict[str, bool]

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global orchestrator
    
    logger.info("Starting Agent Service")
    
    # Initialize orchestrator
    try:
        orchestrator = AgentOrchestrator()
        
        config = {
            "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
            "elevenlabs_api_key": os.getenv("ELEVENLABS_API_KEY"),
            "ollama_url": os.getenv("OLLAMA_URL", "http://ollama:11434"),
            "qdrant_url": os.getenv("QDRANT_URL", "http://qdrant:6333"),
            "smithery_registry_url": os.getenv("SMITHERY_REGISTRY_URL", "https://smithery.ai/api/v1"),
            "mcp_tools_dir": os.getenv("MCP_TOOLS_DIR", "./mcp_tools"),
            "stt_provider": os.getenv("STT_PROVIDER", "whisperx"),
            "tts_provider": os.getenv("TTS_PROVIDER", "coqui"),
            "use_gpu": os.getenv("USE_GPU", "false").lower() == "true"
        }
        
        await orchestrator.initialize(config)
        logger.info("Agent orchestrator initialized successfully")
        
    except Exception as e:
        logger.error("Failed to initialize agent orchestrator", error=str(e))
        raise
    
    yield
    
    logger.info("Shutting down Agent Service")
    if orchestrator:
        await orchestrator.shutdown()

# Create FastAPI app
app = FastAPI(
    title="Jarvis Agent Service",
    description="Multi-agent orchestration service for the Jarvis AI system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        status = await orchestrator.get_system_status()
        overall_health = "healthy" if status.get("orchestrator_initialized", False) else "degraded"
        
        return {
            "status": overall_health,
            "uptime_seconds": int(time.time() - startup_time),
            "agents_count": len(status.get("agents", {})),
            "active_sessions": status.get("active_sessions", 0),
            "timestamp": time.time()
        }
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Health check failed: {e}")

@app.post("/tasks/process", response_model=TaskProcessResponse)
async def process_task(request: TaskProcessRequest, background_tasks: BackgroundTasks):
    """Process a task through the agent system."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        logger.info("Processing task request",
                   session_id=request.session_id,
                   content_length=len(request.content))
        
        session_id = UUID(request.session_id)
        
        result = await orchestrator.process_user_task(
            content=request.content,
            session_id=session_id,
            context=request.context
        )
        
        # Log metrics in background
        background_tasks.add_task(
            log_task_metrics,
            result.agent_id,
            result.processing_time_ms,
            result.tokens_used,
            result.success
        )
        
        return TaskProcessResponse(
            task_id=str(result.task_id),
            result=result.result,
            success=result.success,
            agent_id=result.agent_id,
            tokens_used=result.tokens_used,
            cost=result.cost,
            processing_time_ms=result.processing_time_ms,
            metadata=result.metadata
        )
        
    except ValueError as e:
        logger.error("Invalid task request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Task processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Task processing failed: {e}")

@app.post("/voice/process", response_model=VoiceProcessResponse)
async def process_voice(request: VoiceProcessRequest, background_tasks: BackgroundTasks):
    """Process a voice request (STT or TTS)."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        logger.info("Processing voice request",
                   operation=request.operation,
                   session_id=request.session_id,
                   data_length=len(request.data))
        
        session_id = UUID(request.session_id)
        
        result = await orchestrator.process_voice_request(
            operation=request.operation,
            data=request.data,
            session_id=session_id,
            config=request.config
        )
        
        # Log metrics in background
        background_tasks.add_task(
            log_voice_metrics,
            request.operation,
            result.get("processing_time_ms", 0),
            result.get("success", False)
        )
        
        return VoiceProcessResponse(
            success=result.get("success", False),
            result=result,
            error=result.get("error")
        )
        
    except ValueError as e:
        logger.error("Invalid voice request", error=str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Voice processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {e}")

@app.get("/status", response_model=SystemStatusResponse)
async def get_system_status():
    """Get comprehensive system status."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        status = await orchestrator.get_system_status()
        
        return SystemStatusResponse(
            status="healthy" if status.get("orchestrator_initialized", False) else "degraded",
            uptime_seconds=status.get("uptime_seconds", 0),
            agents={agent_id: agent_status.__dict__ for agent_id, agent_status in status.get("agents", {}).items()},
            active_sessions=status.get("active_sessions", 0),
            total_tasks_processed=status.get("total_tasks_processed", 0),
            supporting_systems=status.get("supporting_systems", {})
        )
        
    except Exception as e:
        logger.error("Failed to get system status", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get system status: {e}")

@app.get("/agents")
async def list_agents():
    """List all available agents."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        status = await orchestrator.get_system_status()
        agents = status.get("agents", {})
        
        return {
            "agents": [
                {
                    "id": agent_id,
                    "name": agent_status.name,
                    "status": agent_status.status,
                    "tasks_completed": agent_status.tasks_completed,
                    "tasks_failed": agent_status.tasks_failed,
                    "average_response_time_ms": agent_status.average_response_time_ms
                }
                for agent_id, agent_status in agents.items()
            ],
            "total_agents": len(agents)
        }
        
    except Exception as e:
        logger.error("Failed to list agents", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {e}")

@app.get("/tools")
async def list_tools():
    """List available MCP tools."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        if orchestrator.mcp_manager:
            tools = orchestrator.mcp_manager.get_installed_tools()
            return {
                "tools": [
                    {
                        "name": tool.tool_name,
                        "version": tool.version,
                        "status": tool.status.value,
                        "usage_count": tool.usage_count,
                        "success_rate": tool.success_rate,
                        "avg_execution_time_ms": tool.avg_execution_time_ms
                    }
                    for tool in tools
                ],
                "total_tools": len(tools)
            }
        else:
            return {"tools": [], "total_tools": 0}
            
    except Exception as e:
        logger.error("Failed to list tools", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to list tools: {e}")

@app.get("/metrics")
async def get_metrics():
    """Get detailed system metrics."""
    if orchestrator is None or not orchestrator.is_initialized:
        raise HTTPException(status_code=503, detail="Agent orchestrator not initialized")
    
    try:
        status = await orchestrator.get_system_status()
        
        # Calculate aggregate metrics
        agents = status.get("agents", {})
        total_tasks = sum(agent.tasks_completed for agent in agents.values())
        total_failures = sum(agent.tasks_failed for agent in agents.values())
        success_rate = total_tasks / max(1, total_tasks + total_failures)
        
        return {
            "system": {
                "uptime_seconds": status.get("uptime_seconds", 0),
                "active_sessions": status.get("active_sessions", 0),
                "total_agents": len(agents)
            },
            "tasks": {
                "total_processed": total_tasks,
                "total_failed": total_failures,
                "success_rate": success_rate
            },
            "agents": {
                agent_id: {
                    "tasks_completed": agent.tasks_completed,
                    "tasks_failed": agent.tasks_failed,
                    "average_response_time_ms": agent.average_response_time_ms,
                    "total_tokens_used": agent.total_tokens_used
                }
                for agent_id, agent in agents.items()
            }
        }
        
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get metrics: {e}")

# Background task functions
async def log_task_metrics(agent_id: str, processing_time_ms: int, tokens_used: int, success: bool):
    """Log task processing metrics."""
    logger.info("Task metrics",
               agent_id=agent_id,
               processing_time_ms=processing_time_ms,
               tokens_used=tokens_used,
               success=success)

async def log_voice_metrics(operation: str, processing_time_ms: int, success: bool):
    """Log voice processing metrics."""
    logger.info("Voice metrics",
               operation=operation,
               processing_time_ms=processing_time_ms,
               success=success)

# Error handlers
@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error("Unexpected error", error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": "An unexpected error occurred"}
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "agent_service:app",
        host="0.0.0.0",
        port=8001,
        reload=True,
        log_level="info"
    )
