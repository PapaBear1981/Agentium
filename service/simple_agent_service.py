#!/usr/bin/env python3
"""
Simple Agent Service for Jarvis AI System
A minimal implementation to get the system running.
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import structlog
import httpx

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

# Pydantic models
class TaskRequest(BaseModel):
    content: str
    session_id: str
    context: Optional[Dict[str, Any]] = {}

class TaskResponse(BaseModel):
    task_id: str
    session_id: str
    content: str
    agent_id: str
    processing_time_ms: float
    success: bool
    error: Optional[str] = None

class HealthResponse(BaseModel):
    status: str
    agents: List[str]
    uptime_seconds: float
    timestamp: float

class SimpleAgentOrchestrator:
    """Simplified agent orchestrator without AutoGen complexity."""
    
    def __init__(self):
        self.agents = {
            "gpt4o_agent": "OpenRouter GPT-4o Agent",
            "gemini_agent": "OpenRouter Gemini Agent", 
            "primary_agent": "Primary Agent"
        }
        self.startup_time = time.time()
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        
    async def initialize(self):
        """Initialize the orchestrator."""
        logger.info("Initializing SimpleAgentOrchestrator")
        if not self.openrouter_api_key:
            logger.warning("No OpenRouter API key found, using mock responses")
        logger.info("Agent orchestrator initialized", agents=list(self.agents.keys()))
        
    async def process_task(self, request: TaskRequest) -> TaskResponse:
        """Process a user task."""
        start_time = time.time()
        task_id = str(uuid4())
        
        try:
            logger.info("Processing task", task_id=task_id, session_id=request.session_id)
            
            # Simple agent selection based on content
            agent_id = self._select_agent(request.content)
            
            # Generate response
            if self.openrouter_api_key:
                response_content = await self._call_openrouter(request.content, agent_id)
            else:
                response_content = self._generate_mock_response(request.content, agent_id)
            
            processing_time = (time.time() - start_time) * 1000
            
            return TaskResponse(
                task_id=task_id,
                session_id=request.session_id,
                content=response_content,
                agent_id=agent_id,
                processing_time_ms=processing_time,
                success=True
            )
            
        except Exception as e:
            processing_time = (time.time() - start_time) * 1000
            logger.error("Task processing failed", error=str(e), task_id=task_id)
            
            return TaskResponse(
                task_id=task_id,
                session_id=request.session_id,
                content=f"Error processing task: {str(e)}",
                agent_id="error_handler",
                processing_time_ms=processing_time,
                success=False,
                error=str(e)
            )
    
    def _select_agent(self, content: str) -> str:
        """Select appropriate agent based on content."""
        content_lower = content.lower()
        
        if any(keyword in content_lower for keyword in ["code", "programming", "technical"]):
            return "gpt4o_agent"
        elif any(keyword in content_lower for keyword in ["search", "research", "find"]):
            return "gemini_agent"
        else:
            return "primary_agent"
    
    async def _call_openrouter(self, content: str, agent_id: str) -> str:
        """Call OpenRouter API."""
        model_map = {
            "gpt4o_agent": "openai/gpt-4o",
            "gemini_agent": "google/gemini-2.0-flash-exp:free",
            "primary_agent": "openai/gpt-4o-mini"
        }
        
        model = model_map.get(agent_id, "openai/gpt-4o-mini")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": "You are Jarvis, a helpful AI assistant."},
                        {"role": "user", "content": content}
                    ]
                },
                timeout=30.0
            )
            
        if response.status_code == 200:
            data = response.json()
            return data["choices"][0]["message"]["content"]
        else:
            logger.error("OpenRouter API error", status=response.status_code, response=response.text)
            return f"I apologize, but I encountered an error processing your request. (Status: {response.status_code})"
    
    def _generate_mock_response(self, content: str, agent_id: str) -> str:
        """Generate a mock response when no API key is available."""
        responses = {
            "gpt4o_agent": f"[GPT-4o Agent] I understand you're asking about: '{content}'. I'm a technical assistant and would normally provide detailed technical guidance here.",
            "gemini_agent": f"[Gemini Agent] I can help you research: '{content}'. I would typically search and provide comprehensive information on this topic.",
            "primary_agent": f"[Primary Agent] Thank you for your message: '{content}'. I'm here to help with various tasks and questions."
        }
        
        return responses.get(agent_id, f"[Agent {agent_id}] I received your message: '{content}' and would process it accordingly.")
    
    async def get_status(self) -> Dict[str, Any]:
        """Get system status."""
        return {
            "status": "healthy",
            "agents": list(self.agents.keys()),
            "uptime_seconds": time.time() - self.startup_time,
            "timestamp": time.time(),
            "has_openrouter_key": bool(self.openrouter_api_key)
        }

# Create FastAPI app
app = FastAPI(title="Jarvis Agent Service", description="Simple Agent Service for Jarvis AI System")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global orchestrator instance
orchestrator = SimpleAgentOrchestrator()

@app.on_event("startup")
async def startup_event():
    """Initialize the orchestrator on startup."""
    await orchestrator.initialize()

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    status = await orchestrator.get_status()
    return HealthResponse(
        status=status["status"],
        agents=status["agents"],
        uptime_seconds=status["uptime_seconds"],
        timestamp=status["timestamp"]
    )

@app.post("/tasks/process", response_model=TaskResponse)
async def process_task(request: TaskRequest):
    """Process a user task."""
    return await orchestrator.process_task(request)

@app.get("/agents")
async def list_agents():
    """List available agents."""
    return {"agents": list(orchestrator.agents.keys())}

@app.get("/tools")
async def list_tools():
    """List available tools."""
    # For the simple implementation, return an empty tools list
    # In the future, this could integrate with MCP tools
    return {
        "tools": [],
        "total_tools": 0,
        "note": "Tools functionality not implemented in simple agent service"
    }

@app.get("/status")
async def get_status():
    """Get detailed system status."""
    return await orchestrator.get_status()

@app.get("/metrics")
async def get_metrics():
    """Get system metrics."""
    status = await orchestrator.get_status()
    return {
        "uptime_seconds": status["uptime_seconds"],
        "agents_count": len(status["agents"]),
        "has_api_key": status["has_openrouter_key"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)