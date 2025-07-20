"""
WebSocket message models for real-time communication.

These models define the structure of messages sent between the client
and server over WebSocket connections.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

class WebSocketMessageType(str, Enum):
    # Client to Server
    VOICE_INPUT = "voice_input"
    TEXT_INPUT = "text_input"
    SYSTEM_COMMAND = "system_command"
    
    # Server to Client
    AGENT_RESPONSE = "agent_response"
    AGENT_RESPONSE_STREAM = "agent_response_stream"
    AGENT_RESPONSE_COMPLETE = "agent_response_complete"
    TOOL_EXECUTION = "tool_execution"
    SYSTEM_STATUS = "system_status"
    COST_UPDATE = "cost_update"
    ERROR = "error"
    
    # Bidirectional
    HEARTBEAT = "heartbeat"
    CONNECTION_STATUS = "connection_status"

class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""
    type: WebSocketMessageType
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: Optional[str] = None
    message_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Decimal: lambda v: float(v)
        }

# Client to Server Messages
class VoiceInputData(BaseModel):
    audio: str  # base64 encoded audio
    format: str = "wav"  # wav, mp3, webm, etc.
    sample_rate: int = 16000
    channels: int = 1
    duration_ms: Optional[int] = None

class VoiceInputMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.VOICE_INPUT
    data: VoiceInputData

class TextInputData(BaseModel):
    message: str
    context: Optional[Dict[str, Any]] = None
    agent_preference: Optional[str] = None

class TextInputMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.TEXT_INPUT
    data: TextInputData

class SystemCommandData(BaseModel):
    command: str  # pause, resume, reset, status, stop
    parameters: Optional[Dict[str, Any]] = None

class SystemCommandMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.SYSTEM_COMMAND
    data: SystemCommandData

# Server to Client Messages
class AgentResponseData(BaseModel):
    agent_id: str
    agent_name: str
    message: str
    audio: Optional[str] = None  # base64 encoded TTS audio
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    cost: Decimal = Decimal("0.00")
    model: str
    processing_time_ms: Optional[int] = None

class AgentResponseMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.AGENT_RESPONSE
    data: AgentResponseData

class AgentResponseStreamData(BaseModel):
    agent_id: str
    chunk: str
    is_final: bool = False
    chunk_index: int = 0

class AgentResponseStreamMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.AGENT_RESPONSE_STREAM
    data: AgentResponseStreamData

class AgentResponseCompleteData(BaseModel):
    agent_id: str
    total_tokens: int
    total_cost: Decimal
    processing_time_ms: int

class AgentResponseCompleteMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.AGENT_RESPONSE_COMPLETE
    data: AgentResponseCompleteData

class ToolExecutionData(BaseModel):
    tool_name: str
    status: str  # started, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: Optional[int] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.TOOL_EXECUTION
    data: ToolExecutionData

class SystemStatusData(BaseModel):
    agents_active: int
    agents_idle: int
    agents_error: int
    session_cost: Decimal
    budget_remaining: Decimal
    voice_processing: bool
    tools_available: int
    system_health: str  # healthy, degraded, unhealthy
    uptime_seconds: int

class SystemStatusMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.SYSTEM_STATUS
    data: SystemStatusData

class CostUpdateData(BaseModel):
    session_cost: Decimal
    last_operation_cost: Decimal
    budget_remaining: Decimal
    budget_limit: Decimal
    warning: Optional[str] = None
    cost_breakdown: Dict[str, Decimal] = Field(default_factory=dict)

class CostUpdateMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.COST_UPDATE
    data: CostUpdateData

class ErrorData(BaseModel):
    error_code: str
    error_message: str
    error_details: Optional[Dict[str, Any]] = None
    recoverable: bool = True

class ErrorMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.ERROR
    data: ErrorData

class HeartbeatData(BaseModel):
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    server_time: Optional[datetime] = None

class HeartbeatMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.HEARTBEAT
    data: HeartbeatData

class ConnectionStatusData(BaseModel):
    status: str  # connected, disconnected, reconnecting
    session_id: str
    client_count: Optional[int] = None
    server_version: Optional[str] = None

class ConnectionStatusMessage(WebSocketMessage):
    type: WebSocketMessageType = WebSocketMessageType.CONNECTION_STATUS
    data: ConnectionStatusData

# Utility functions for message creation
def create_voice_input_message(
    audio: str,
    format: str = "wav",
    sample_rate: int = 16000,
    session_id: Optional[str] = None
) -> VoiceInputMessage:
    """Create a voice input message."""
    return VoiceInputMessage(
        data=VoiceInputData(
            audio=audio,
            format=format,
            sample_rate=sample_rate
        ),
        session_id=session_id
    )

def create_text_input_message(
    message: str,
    context: Optional[Dict[str, Any]] = None,
    session_id: Optional[str] = None
) -> TextInputMessage:
    """Create a text input message."""
    return TextInputMessage(
        data=TextInputData(
            message=message,
            context=context
        ),
        session_id=session_id
    )

def create_agent_response_message(
    agent_id: str,
    agent_name: str,
    message: str,
    model: str,
    tokens_used: int = 0,
    cost: Decimal = Decimal("0.00"),
    audio: Optional[str] = None,
    session_id: Optional[str] = None
) -> AgentResponseMessage:
    """Create an agent response message."""
    return AgentResponseMessage(
        data=AgentResponseData(
            agent_id=agent_id,
            agent_name=agent_name,
            message=message,
            model=model,
            tokens_used=tokens_used,
            cost=cost,
            audio=audio
        ),
        session_id=session_id
    )

def create_error_message(
    error_code: str,
    error_message: str,
    error_details: Optional[Dict[str, Any]] = None,
    recoverable: bool = True,
    session_id: Optional[str] = None
) -> ErrorMessage:
    """Create an error message."""
    return ErrorMessage(
        data=ErrorData(
            error_code=error_code,
            error_message=error_message,
            error_details=error_details,
            recoverable=recoverable
        ),
        session_id=session_id
    )

def create_system_status_message(
    agents_active: int,
    session_cost: Decimal,
    budget_remaining: Decimal,
    voice_processing: bool = False,
    session_id: Optional[str] = None
) -> SystemStatusMessage:
    """Create a system status message."""
    return SystemStatusMessage(
        data=SystemStatusData(
            agents_active=agents_active,
            agents_idle=0,
            agents_error=0,
            session_cost=session_cost,
            budget_remaining=budget_remaining,
            voice_processing=voice_processing,
            tools_available=0,
            system_health="healthy",
            uptime_seconds=0
        ),
        session_id=session_id
    )
