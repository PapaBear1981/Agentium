"""
FastAPI WebSocket Frontend for Jarvis Multi-Agent AI System.

This module provides real-time WebSocket communication between clients
and the agent system, supporting voice input/output and text chat.
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Set
from uuid import UUID, uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import httpx
import structlog

from models.websocket import (
    WebSocketMessage, WebSocketMessageType, VoiceInputMessage, TextInputMessage,
    SystemCommandMessage, AgentResponseMessage, ToolExecutionMessage,
    SystemStatusMessage, CostUpdateMessage, ErrorMessage,
    create_agent_response_message, create_error_message, create_system_status_message
)
from models.voice import STTRequest, TTSRequest

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

class ConnectionManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_data: Dict[str, Dict] = {}
        
    async def connect(self, websocket: WebSocket, session_id: str):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_data[session_id] = {
            "connected_at": time.time(),
            "message_count": 0,
            "last_activity": time.time()
        }
        logger.info("WebSocket connected", session_id=session_id)
    
    def disconnect(self, session_id: str):
        """Remove a WebSocket connection."""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_data:
            del self.session_data[session_id]
        logger.info("WebSocket disconnected", session_id=session_id)
    
    async def send_message(self, session_id: str, message: WebSocketMessage):
        """Send a message to a specific session."""
        if session_id in self.active_connections:
            try:
                websocket = self.active_connections[session_id]
                await websocket.send_text(message.model_dump_json())
                
                # Update session activity
                if session_id in self.session_data:
                    self.session_data[session_id]["last_activity"] = time.time()
                    self.session_data[session_id]["message_count"] += 1
                    
            except Exception as e:
                logger.error("Failed to send WebSocket message", 
                           session_id=session_id, error=str(e))
                self.disconnect(session_id)
    
    async def broadcast(self, message: WebSocketMessage):
        """Broadcast a message to all connected sessions."""
        disconnected = []
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(message.model_dump_json())
            except Exception as e:
                logger.error("Failed to broadcast message", 
                           session_id=session_id, error=str(e))
                disconnected.append(session_id)
        
        # Clean up disconnected sessions
        for session_id in disconnected:
            self.disconnect(session_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_session_info(self, session_id: str) -> Optional[Dict]:
        """Get information about a specific session."""
        return self.session_data.get(session_id)

class JarvisWebSocketHandler:
    """Handles WebSocket message processing and agent communication."""
    
    def __init__(self, agent_service_url: str, voice_service_url: str):
        self.agent_service_url = agent_service_url
        self.voice_service_url = voice_service_url
        self.http_client = httpx.AsyncClient(timeout=60.0)
        
        # Session state tracking
        self.session_states: Dict[str, Dict] = {}
        
    async def handle_message(self, session_id: str, message_data: Dict, connection_manager: ConnectionManager):
        """Handle incoming WebSocket message."""
        try:
            message_type = message_data.get("type")
            data = message_data.get("data", {})
            
            logger.info("Processing WebSocket message",
                       session_id=session_id,
                       message_type=message_type)
            
            # Initialize session state if needed
            if session_id not in self.session_states:
                self.session_states[session_id] = {
                    "created_at": time.time(),
                    "total_cost": 0.0,
                    "message_history": [],
                    "voice_enabled": True,
                    "current_agent": None
                }
            
            session_state = self.session_states[session_id]
            
            if message_type == WebSocketMessageType.VOICE_INPUT:
                await self._handle_voice_input(session_id, data, connection_manager, session_state)
            elif message_type == WebSocketMessageType.TEXT_INPUT:
                await self._handle_text_input(session_id, data, connection_manager, session_state)
            elif message_type == WebSocketMessageType.SYSTEM_COMMAND:
                await self._handle_system_command(session_id, data, connection_manager, session_state)
            elif message_type == WebSocketMessageType.HEARTBEAT:
                await self._handle_heartbeat(session_id, data, connection_manager)
            else:
                logger.warning("Unknown message type", message_type=message_type)
                error_msg = create_error_message(
                    error_code="UNKNOWN_MESSAGE_TYPE",
                    error_message=f"Unknown message type: {message_type}",
                    session_id=session_id
                )
                await connection_manager.send_message(session_id, error_msg)
                
        except Exception as e:
            logger.error("Error handling WebSocket message", 
                        session_id=session_id, error=str(e))
            error_msg = create_error_message(
                error_code="MESSAGE_PROCESSING_ERROR",
                error_message=f"Failed to process message: {str(e)}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _handle_voice_input(self, session_id: str, data: Dict, connection_manager: ConnectionManager, session_state: Dict):
        """Handle voice input message."""
        try:
            # First, convert speech to text
            stt_response = await self.http_client.post(
                f"{self.voice_service_url}/stt",
                json={
                    "audio_data": data.get("audio"),
                    "format": data.get("format", "wav"),
                    "sample_rate": data.get("sample_rate", 16000),
                    "session_id": session_id
                }
            )
            stt_response.raise_for_status()
            stt_result = stt_response.json()
            
            if not stt_result.get("success"):
                raise Exception(f"STT failed: {stt_result.get('error', 'Unknown error')}")
            
            text = stt_result.get("text", "")
            if not text.strip():
                logger.warning("Empty transcription result", session_id=session_id)
                return
            
            logger.info("Voice transcribed", session_id=session_id, text=text)
            
            # Process the transcribed text as a regular text input
            await self._process_text_with_agent(session_id, text, connection_manager, session_state, is_voice=True)
            
        except Exception as e:
            logger.error("Voice input processing failed", session_id=session_id, error=str(e))
            error_msg = create_error_message(
                error_code="VOICE_PROCESSING_ERROR",
                error_message=f"Voice processing failed: {str(e)}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _handle_text_input(self, session_id: str, data: Dict, connection_manager: ConnectionManager, session_state: Dict):
        """Handle text input message."""
        try:
            message = data.get("message", "").strip()
            if not message:
                return
            
            context = data.get("context", {})
            agent_preference = data.get("agent_preference")
            
            await self._process_text_with_agent(session_id, message, connection_manager, session_state, context=context)
            
        except Exception as e:
            logger.error("Text input processing failed", session_id=session_id, error=str(e))
            error_msg = create_error_message(
                error_code="TEXT_PROCESSING_ERROR",
                error_message=f"Text processing failed: {str(e)}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _process_text_with_agent(self, session_id: str, text: str, connection_manager: ConnectionManager, 
                                     session_state: Dict, context: Optional[Dict] = None, is_voice: bool = False):
        """Process text through the agent system."""
        try:
            # Send to agent service
            agent_response = await self.http_client.post(
                f"{self.agent_service_url}/tasks/process",
                json={
                    "content": text,
                    "session_id": session_id,
                    "context": context or {},
                    "priority": "medium"
                }
            )
            agent_response.raise_for_status()
            agent_result = agent_response.json()
            
            # Update session state
            session_state["total_cost"] += agent_result.get("cost", 0.0)
            session_state["current_agent"] = agent_result.get("agent_id")
            session_state["message_history"].append({
                "user_message": text,
                "agent_response": agent_result.get("result"),
                "timestamp": time.time(),
                "is_voice": is_voice
            })
            
            # Prepare response message
            response_text = agent_result.get("result", "")
            
            # Convert to speech if this was a voice input
            audio_data = None
            if is_voice and session_state.get("voice_enabled", True):
                try:
                    tts_response = await self.http_client.post(
                        f"{self.voice_service_url}/tts",
                        json={
                            "text": response_text,
                            "session_id": session_id,
                            "voice": "default",
                            "speed": 1.0
                        }
                    )
                    tts_response.raise_for_status()
                    tts_result = tts_response.json()
                    
                    if tts_result.get("success"):
                        audio_data = tts_result.get("audio_data")
                    
                except Exception as e:
                    logger.warning("TTS failed", session_id=session_id, error=str(e))
            
            # Send agent response
            agent_msg = create_agent_response_message(
                agent_id=agent_result.get("agent_id", "unknown"),
                agent_name=agent_result.get("agent_id", "Unknown Agent"),
                message=response_text,
                model=agent_result.get("metadata", {}).get("model", "unknown"),
                tokens_used=agent_result.get("tokens_used", 0),
                cost=agent_result.get("cost", 0.0),
                audio=audio_data,
                session_id=session_id
            )
            await connection_manager.send_message(session_id, agent_msg)
            
            # Send cost update
            cost_msg = CostUpdateMessage(
                data={
                    "session_cost": session_state["total_cost"],
                    "last_operation_cost": agent_result.get("cost", 0.0),
                    "budget_remaining": 100.0 - session_state["total_cost"],  # Assuming $100 budget
                    "budget_limit": 100.0
                },
                session_id=session_id
            )
            await connection_manager.send_message(session_id, cost_msg)
            
        except Exception as e:
            logger.error("Agent processing failed", session_id=session_id, error=str(e))
            error_msg = create_error_message(
                error_code="AGENT_PROCESSING_ERROR",
                error_message=f"Agent processing failed: {str(e)}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _handle_system_command(self, session_id: str, data: Dict, connection_manager: ConnectionManager, session_state: Dict):
        """Handle system command message."""
        command = data.get("command")
        parameters = data.get("parameters", {})
        
        if command == "status":
            # Get system status
            try:
                status_response = await self.http_client.get(f"{self.agent_service_url}/status")
                status_response.raise_for_status()
                status_data = status_response.json()
                
                # Handle agents list (current format) or dict (legacy format)
                agents_data = status_data.get("agents", [])
                if isinstance(agents_data, list):
                    agents_active = len(agents_data)  # All agents in list are considered active
                else:
                    agents_active = len([a for a in agents_data.values() if a.get("status") == "active"])
                
                status_msg = create_system_status_message(
                    agents_active=agents_active,
                    session_cost=session_state.get("total_cost", 0.0),
                    budget_remaining=100.0 - session_state.get("total_cost", 0.0),
                    voice_processing=session_state.get("voice_enabled", True),
                    session_id=session_id
                )
                await connection_manager.send_message(session_id, status_msg)
                
            except Exception as e:
                logger.error("Failed to get system status", error=str(e))
        
        elif command == "pause":
            session_state["paused"] = True
            logger.info("Session paused", session_id=session_id)
        
        elif command == "resume":
            session_state["paused"] = False
            logger.info("Session resumed", session_id=session_id)
        
        elif command == "reset":
            # Reset session state
            session_state.clear()
            session_state.update({
                "created_at": time.time(),
                "total_cost": 0.0,
                "message_history": [],
                "voice_enabled": True,
                "current_agent": None
            })
            logger.info("Session reset", session_id=session_id)
    
    async def _handle_heartbeat(self, session_id: str, data: Dict, connection_manager: ConnectionManager):
        """Handle heartbeat message."""
        # Simply echo back the heartbeat
        heartbeat_msg = WebSocketMessage(
            type=WebSocketMessageType.HEARTBEAT,
            data={"timestamp": time.time(), "server_time": time.time()},
            session_id=session_id
        )
        await connection_manager.send_message(session_id, heartbeat_msg)
    
    async def cleanup(self):
        """Cleanup resources."""
        await self.http_client.aclose()

# Global instances
connection_manager = ConnectionManager()
websocket_handler: Optional[JarvisWebSocketHandler] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global websocket_handler
    
    logger.info("Starting Jarvis WebSocket Frontend")
    
    # Initialize WebSocket handler
    agent_service_url = os.getenv("AGENT_SERVICE_URL", "http://agent_service:8001")
    voice_service_url = os.getenv("VOICE_SERVICE_URL", "http://voice_adapter:8002")
    
    websocket_handler = JarvisWebSocketHandler(agent_service_url, voice_service_url)
    
    logger.info("WebSocket handler initialized")
    
    yield
    
    logger.info("Shutting down Jarvis WebSocket Frontend")
    if websocket_handler:
        await websocket_handler.cleanup()

# Create FastAPI app
app = FastAPI(
    title="Jarvis WebSocket Frontend",
    description="Real-time WebSocket communication for the Jarvis multi-agent AI system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for real-time communication."""
    await connection_manager.connect(websocket, session_id)

    try:
        # Send initial connection status
        connection_msg = WebSocketMessage(
            type=WebSocketMessageType.CONNECTION_STATUS,
            data={
                "status": "connected",
                "session_id": session_id,
                "server_version": "1.0.0"
            },
            session_id=session_id
        )
        await connection_manager.send_message(session_id, connection_msg)

        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)

            # Process message
            if websocket_handler:
                await websocket_handler.handle_message(session_id, message_data, connection_manager)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
    finally:
        connection_manager.disconnect(session_id)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "active_connections": connection_manager.get_connection_count(),
        "timestamp": time.time()
    }

@app.get("/connections")
async def get_connections():
    """Get information about active connections."""
    return {
        "active_connections": connection_manager.get_connection_count(),
        "sessions": {
            session_id: {
                "connected_at": session_data["connected_at"],
                "message_count": session_data["message_count"],
                "last_activity": session_data["last_activity"],
                "duration_seconds": int(time.time() - session_data["connected_at"])
            }
            for session_id, session_data in connection_manager.session_data.items()
        }
    }

@app.post("/broadcast")
async def broadcast_message(message: Dict):
    """Broadcast a message to all connected clients."""
    try:
        ws_message = WebSocketMessage(
            type=WebSocketMessageType.SYSTEM_STATUS,
            data=message,
            timestamp=time.time()
        )
        await connection_manager.broadcast(ws_message)

        return {
            "success": True,
            "message": "Message broadcasted",
            "recipients": connection_manager.get_connection_count()
        }
    except Exception as e:
        logger.error("Broadcast failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Broadcast failed: {e}")

@app.get("/sessions/{session_id}")
async def get_session_info(session_id: str):
    """Get information about a specific session."""
    session_info = connection_manager.get_session_info(session_id)

    if not session_info:
        raise HTTPException(status_code=404, detail="Session not found")

    # Add session state if available
    if websocket_handler and session_id in websocket_handler.session_states:
        session_state = websocket_handler.session_states[session_id]
        session_info.update({
            "total_cost": session_state.get("total_cost", 0.0),
            "message_history_count": len(session_state.get("message_history", [])),
            "voice_enabled": session_state.get("voice_enabled", True),
            "current_agent": session_state.get("current_agent")
        })

    return session_info

@app.delete("/sessions/{session_id}")
async def disconnect_session(session_id: str):
    """Forcefully disconnect a session."""
    if session_id in connection_manager.active_connections:
        websocket = connection_manager.active_connections[session_id]
        await websocket.close()
        connection_manager.disconnect(session_id)

        return {"success": True, "message": f"Session {session_id} disconnected"}
    else:
        raise HTTPException(status_code=404, detail="Session not found")

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "service": "Jarvis WebSocket Frontend",
        "version": "1.0.0",
        "description": "Real-time WebSocket communication for the Jarvis multi-agent AI system",
        "endpoints": {
            "websocket": "/ws/{session_id}",
            "health": "/health",
            "connections": "/connections",
            "broadcast": "/broadcast",
            "sessions": "/sessions/{session_id}"
        },
        "active_connections": connection_manager.get_connection_count(),
        "timestamp": time.time()
    }

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
        "frontend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
