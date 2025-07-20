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
        # File-based debug at the very start
        with open("/app/debug.log", "a") as f:
            f.write(f"[DEBUG] handle_message called: session_id={session_id}, message_data={message_data}\n")
            f.flush()
        
        try:
            message_type = message_data.get("type")
            data = message_data.get("data", {})
            
            with open("/app/debug.log", "a") as f:
                f.write(f"[DEBUG] Parsed: type={message_type}, data={data}\n")
                f.flush()
            
            print(f"[DEBUG] WebSocket message received: type={message_type}, data={data}")
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
            
            logger.debug("Received WebSocket message for processing",
                         session_id=session_id,
                         message_type=message_type,
                         message_data=message_data)
            
            if message_type == WebSocketMessageType.VOICE_INPUT:
                logger.info("Handling voice input", session_id=session_id)
                await self._handle_voice_input(session_id, data, connection_manager, session_state)
            elif message_type == WebSocketMessageType.TEXT_INPUT:
                logger.info("Handling text input", session_id=session_id)
                await self._handle_text_input(session_id, data, connection_manager, session_state)
            elif message_type == WebSocketMessageType.SYSTEM_COMMAND:
                logger.info("Handling system command", session_id=session_id)
                await self._handle_system_command(session_id, data, connection_manager, session_state)
            elif message_type == WebSocketMessageType.HEARTBEAT:
                logger.info("Handling heartbeat", session_id=session_id)
                await self._handle_heartbeat(session_id, data, connection_manager)
            else:
                logger.warning("Unknown message type received", message_type=message_type, session_id=session_id)
                error_msg = create_error_message(
                    error_code="UNKNOWN_MESSAGE_TYPE",
                    error_message=f"Unknown message type: {message_type}",
                    session_id=session_id
                )
                await connection_manager.send_message(session_id, error_msg)
                
        except Exception as e:
            logger.error("Error handling WebSocket message",
                        session_id=session_id, error=str(e), exc_info=True)
            error_msg = create_error_message(
                error_code="MESSAGE_PROCESSING_ERROR",
                error_message=f"Failed to process message: {str(e)}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _handle_voice_input(self, session_id: str, data: Dict, connection_manager: ConnectionManager, session_state: Dict):
        """Handle voice input message."""
        try:
            logger.debug("Initiating STT request to voice service", session_id=session_id)
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
            logger.debug("STT response received", session_id=session_id, stt_result=stt_result)
            
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
            logger.error("Voice input processing failed", session_id=session_id, error=str(e), exc_info=True)
            error_msg = create_error_message(
                error_code="VOICE_PROCESSING_ERROR",
                error_message=f"Voice processing failed: {str(e)}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _handle_text_input(self, session_id: str, data: Dict, connection_manager: ConnectionManager, session_state: Dict):
        """Handle text input message."""
        print(f"[DEBUG] Processing text input for session {session_id}: {data}")
        logger.info("Processing text input", session_id=session_id, data=data)
        
        try:
            message = data.get("message", "").strip()
            if not message:
                logger.warning("Empty text message received", session_id=session_id)
                return
            
            context = data.get("context", {})
            # agent_preference = data.get("agent_preference") # Not used
            
            # File-based debug for text input handler
            with open("/app/debug.log", "a") as f:
                f.write(f"[DEBUG] Text input handler - message: '{message}'\n")
                f.write(f"[DEBUG] About to call _process_text_with_agent\n")
                f.flush()
            
            logger.debug("Calling _process_text_with_agent for text input", session_id=session_id, message=message)
            await self._process_text_with_agent(session_id, message, connection_manager, session_state, context=context)
            
        except Exception as e:
            logger.error("Text input processing failed", session_id=session_id, error=str(e), exc_info=True)
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
            # File-based debug for agent service call
            with open("/app/debug.log", "a") as f:
                f.write(f"[DEBUG] Sending to agent service: {self.agent_service_url}\n")
                f.write(f"[DEBUG] Text: {text}\n")
                f.flush()
            
            logger.info("Sending text to agent service",
                        session_id=session_id,
                        agent_service_url=self.agent_service_url,
                        content_length=len(text))
            
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
            logger.info("Received response from agent service",
                        session_id=session_id,
                        agent_result_success=agent_result.get("success"),
                        agent_id=agent_result.get("agent_id"),
                        agent_content_length=len(str(agent_result.get('content', ''))))
            
            # Update session state
            session_state["total_cost"] += agent_result.get("cost", 0.0)
            session_state["current_agent"] = agent_result.get("agent_id")
            session_state["message_history"].append({
                "user_message": text,
                "agent_response": agent_result.get("content"),
                "timestamp": time.time(),
                "is_voice": is_voice
            })
            
            # Log the full agent response content for debugging
            # File-based debug logging
            with open("/app/debug.log", "a") as f:
                f.write(f"[DEBUG] Full agent response: {agent_result}\n")
                f.flush()
            
            response_text = agent_result.get("content", "No content from agent.")
            # Temporary debug: let's hardcode a message to see if it works
            if not response_text.strip():
                response_text = "HARDCODED: Agent response was empty, but this proves WebSocket works!"
            
            with open("/app/debug.log", "a") as f:
                f.write(f"[DEBUG] Extracted response text: '{response_text}' (length: {len(response_text)})\n")
                f.flush()
            
            # Convert to speech if this was a voice input
            audio_data = None
            if is_voice and session_state.get("voice_enabled", True):
                try:
                    logger.debug("Initiating TTS request to voice service", session_id=session_id)
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
                    logger.debug("TTS response received", session_id=session_id, tts_result=tts_result)
                    
                    if tts_result.get("success"):
                        audio_data = tts_result.get("audio_data")
                    
                except Exception as e:
                    logger.warning("TTS failed", session_id=session_id, error=str(e), exc_info=True)
            
            logger.info("Sending agent response message to frontend",
                        session_id=session_id,
                        agent_id=agent_result.get("agent_id", "unknown"),
                        message_type="agent_response",
                        message_length=len(response_text))
            
            # Send agent response
            from decimal import Decimal
            agent_msg = create_agent_response_message(
                agent_id=agent_result.get("agent_id", "unknown"),
                agent_name=agent_result.get("agent_id", "Unknown Agent"),
                message=response_text, # Use the actual response text now
                model=agent_result.get("metadata", {}).get("model", "unknown"),
                tokens_used=agent_result.get("tokens_used", 0),
                cost=Decimal(str(agent_result.get("cost", 0.0))),
                audio=audio_data,
                session_id=session_id
            )
            await connection_manager.send_message(session_id, agent_msg)
            
            # Send cost update
            cost_msg = CostUpdateMessage(
                data={
                    "session_cost": Decimal(str(session_state["total_cost"])),
                    "last_operation_cost": Decimal(str(agent_result.get("cost", 0.0))),
                    "budget_remaining": Decimal(str(100.0 - session_state["total_cost"])),  # Assuming $100 budget
                    "budget_limit": Decimal(str(100.0))
                },
                session_id=session_id
            )
            await connection_manager.send_message(session_id, cost_msg)
            
        except httpx.HTTPStatusError as e:
            logger.error("HTTP error during agent processing", session_id=session_id, error=str(e),
                        request=e.request.url, response_status=e.response.status_code, response_text=e.response.text, exc_info=True)
            error_msg = create_error_message(
                error_code="AGENT_SERVICE_HTTP_ERROR",
                error_message=f"Agent service communication failed: {e.response.status_code} - {e.response.text}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
        except Exception as e:
            logger.error("Agent processing failed (general exception)", session_id=session_id, error=str(e), exc_info=True)
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
        logger.info("Received system command", session_id=session_id, command=command, parameters=parameters)
        
        if command == "status":
            # Get system status
            try:
                logger.debug("Requesting system status from agent service", agent_service_url=self.agent_service_url)
                status_response = await self.http_client.get(f"{self.agent_service_url}/status")
                status_response.raise_for_status()
                status_data = status_response.json()
                logger.debug("System status response received", status_data=status_data)
                
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
                logger.info("System status sent to frontend", session_id=session_id)
                
            except Exception as e:
                logger.error("Failed to get system status", error=str(e), exc_info=True)
                error_msg = create_error_message(
                    error_code="SYSTEM_STATUS_ERROR",
                    error_message=f"Failed to get system status: {str(e)}",
                    session_id=session_id
                )
                await connection_manager.send_message(session_id, error_msg)
        
        elif command == "pause":
            session_state["paused"] = True
            logger.info("Session paused", session_id=session_id)
            system_status = create_system_status_message(
                session_id=session_id, message="Session paused."
            )
            await connection_manager.send_message(session_id, system_status)
        
        elif command == "resume":
            session_state["paused"] = False
            logger.info("Session resumed", session_id=session_id)
            system_status = create_system_status_message(
                session_id=session_id, message="Session resumed."
            )
            await connection_manager.send_message(session_id, system_status)
        
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
            system_status = create_system_status_message(
                session_id=session_id, message="Session reset."
            )
            await connection_manager.send_message(session_id, system_status)
        else:
            logger.warning("Unknown system command recieved", session_id=session_id, command=command)
            error_msg = create_error_message(
                error_code="UNKNOWN_COMMAND",
                error_message=f"Unknown system command: {command}",
                session_id=session_id
            )
            await connection_manager.send_message(session_id, error_msg)
    
    async def _handle_heartbeat(self, session_id: str, data: Dict, connection_manager: ConnectionManager):
        """Handle heartbeat message."""
        logger.debug("Received heartbeat", session_id=session_id, data=data)
        # Simply echo back the heartbeat
        heartbeat_msg = WebSocketMessage(
            type=WebSocketMessageType.HEARTBEAT,
            data={"timestamp": time.time(), "server_time": time.time(), "echo": True},
            session_id=session_id
        )
        await connection_manager.send_message(session_id, heartbeat_msg)
        logger.debug("Sent heartbeat echo", session_id=session_id)
    
    async def cleanup(self):
        """Cleanup resources."""
        if self.http_client:
            await self.http_client.aclose()
            logger.info("HTTP client closed.")

# Global instances
connection_manager = ConnectionManager()
websocket_handler: Optional[JarvisWebSocketHandler] = None

# Environment configuration
AGENT_SERVICE_URL = os.getenv("AGENT_SERVICE_URL", "http://localhost:8001")
VOICE_SERVICE_URL = os.getenv("VOICE_SERVICE_URL", "http://localhost:8002")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8080").split(",")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager."""
    global websocket_handler
    
    # Initialize WebSocket handler
    websocket_handler = JarvisWebSocketHandler(AGENT_SERVICE_URL, VOICE_SERVICE_URL)
    logger.info("WebSocket handler initialized", 
                agent_service_url=AGENT_SERVICE_URL,
                voice_service_url=VOICE_SERVICE_URL)
    
    yield
    
    # Cleanup
    if websocket_handler:
        await websocket_handler.cleanup()
        logger.info("WebSocket handler cleaned up")

# Create FastAPI app
app = FastAPI(
    title="Jarvis WebSocket Frontend",
    description="Real-time WebSocket communication for Jarvis Multi-Agent AI System",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "jarvis-websocket-frontend",
        "active_connections": connection_manager.get_connection_count(),
        "timestamp": time.time()
    }

@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for client connections."""
    await connection_manager.connect(websocket, session_id)
    logger.info("Client connected", session_id=session_id)
    
    # Send connection status message
    try:
        from models.websocket import ConnectionStatusMessage, ConnectionStatusData, WebSocketMessageType
        connection_msg = ConnectionStatusMessage(
            type=WebSocketMessageType.CONNECTION_STATUS,
            data=ConnectionStatusData(
                status="connected",
                session_id=session_id,
                client_count=connection_manager.get_connection_count(),
                server_version="1.0.0"
            ),
            session_id=session_id
        )
        await connection_manager.send_message(session_id, connection_msg)
    except Exception as e:
        logger.error("Failed to send connection status", session_id=session_id, error=str(e))
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            print(f"[DEBUG] Received WebSocket data: {data}")
            message_data = json.loads(data)
            print(f"[DEBUG] Parsed message data: {message_data}")
            
            # File-based debug for WebSocket endpoint
            with open("/app/debug.log", "a") as f:
                f.write(f"[DEBUG] WebSocket endpoint received: {message_data}\n")
                f.write(f"[DEBUG] websocket_handler is: {websocket_handler}\n")
                f.flush()
            
            # Handle the message
            if websocket_handler:
                print(f"[DEBUG] Calling websocket_handler.handle_message")
                with open("/app/debug.log", "a") as f:
                    f.write(f"[DEBUG] About to call handle_message\n")
                    f.flush()
                await websocket_handler.handle_message(session_id, message_data, connection_manager)
            else:
                print(f"[DEBUG] WebSocket handler not initialized!")
                with open("/app/debug.log", "a") as f:
                    f.write(f"[DEBUG] WebSocket handler is None!\n")
                    f.flush()
                logger.error("WebSocket handler not initialized")
                
    except WebSocketDisconnect:
        connection_manager.disconnect(session_id)
        logger.info("Client disconnected", session_id=session_id)
    except Exception as e:
        logger.error("WebSocket error", session_id=session_id, error=str(e))
        connection_manager.disconnect(session_id)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "frontend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
