"""
Database models for the Jarvis Multi-Agent AI System.

These Pydantic models correspond to the PostgreSQL database schema
and provide type safety and validation for database operations.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, Numeric, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

# Enums matching database types
class MessageType(str, Enum):
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    TOOL = "tool"

class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    ERROR = "error"
    MAINTENANCE = "maintenance"

class ToolStatus(str, Enum):
    AVAILABLE = "available"
    INSTALLING = "installing"
    ERROR = "error"
    DEPRECATED = "deprecated"

class SessionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"

# Pydantic models for API serialization
class SessionBase(BaseModel):
    user_id: Optional[str] = None
    status: SessionStatus = SessionStatus.ACTIVE
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SessionCreate(SessionBase):
    pass

class Session(SessionBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime
    updated_at: datetime
    ended_at: Optional[datetime] = None
    total_cost: Decimal = Decimal("0.00")
    total_tokens: int = 0

class ChatLogBase(BaseModel):
    session_id: UUID
    agent_id: Optional[str] = None
    message_type: MessageType
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tokens_used: int = 0
    cost: Decimal = Decimal("0.00")

class ChatLogCreate(ChatLogBase):
    embedding: Optional[List[float]] = None

class ChatLog(ChatLogBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime

class AgentBase(BaseModel):
    name: str
    description: Optional[str] = None
    model_name: str
    model_provider: str
    status: AgentStatus = AgentStatus.IDLE
    system_message: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)

class AgentCreate(AgentBase):
    id: str

class Agent(AgentBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime] = None

class ToolRegistryBase(BaseModel):
    tool_name: str
    tool_version: str
    description: Optional[str] = None
    status: ToolStatus = ToolStatus.AVAILABLE
    config: Dict[str, Any] = Field(default_factory=dict)
    safety_score: Optional[int] = Field(None, ge=0, le=100)
    usage_count: int = 0

class ToolRegistryCreate(ToolRegistryBase):
    pass

class ToolRegistry(ToolRegistryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    install_date: datetime
    last_used: Optional[datetime] = None

class CostHistoryBase(BaseModel):
    session_id: UUID
    agent_id: Optional[str] = None
    model_name: str
    operation_type: str
    tokens_input: int = 0
    tokens_output: int = 0
    cost: Decimal
    metadata: Dict[str, Any] = Field(default_factory=dict)

class CostHistoryCreate(CostHistoryBase):
    pass

class CostHistory(CostHistoryBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    tokens_total: int
    created_at: datetime

class FileIndexBase(BaseModel):
    filename: str
    file_path: str
    file_hash: str
    file_size: int
    mime_type: Optional[str] = None
    chunk_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)

class FileIndexCreate(FileIndexBase):
    pass

class FileIndex(FileIndexBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    upload_date: datetime
    processed_date: Optional[datetime] = None

class DocumentChunkBase(BaseModel):
    file_id: UUID
    chunk_index: int
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentChunkCreate(DocumentChunkBase):
    embedding: Optional[List[float]] = None

class DocumentChunk(DocumentChunkBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime

class ReflexionLogBase(BaseModel):
    session_id: UUID
    task_id: Optional[UUID] = None
    task_description: str
    success: bool
    analysis: Optional[str] = None
    heuristics: List[Dict[str, Any]] = Field(default_factory=list)
    improvement_suggestions: Optional[str] = None
    confidence_score: Optional[Decimal] = Field(None, ge=0, le=1)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ReflexionLogCreate(ReflexionLogBase):
    pass

class ReflexionLog(ReflexionLogBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime

class VoiceLogBase(BaseModel):
    session_id: UUID
    operation_type: str  # 'stt' or 'tts'
    provider: str
    input_format: Optional[str] = None
    output_format: Optional[str] = None
    duration_ms: Optional[int] = None
    processing_time_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class VoiceLogCreate(VoiceLogBase):
    pass

class VoiceLog(VoiceLogBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime

class SystemMetricBase(BaseModel):
    metric_name: str
    metric_value: Decimal
    metric_unit: Optional[str] = None
    component: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class SystemMetricCreate(SystemMetricBase):
    pass

class SystemMetric(SystemMetricBase):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    created_at: datetime

# Summary models for analytics
class SessionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    user_id: Optional[str]
    status: SessionStatus
    created_at: datetime
    total_cost: Decimal
    total_tokens: int
    message_count: int
    agents_used: int

class AgentPerformance(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    model_name: str
    status: AgentStatus
    total_messages: int
    total_tokens: int
    total_cost: Decimal
    avg_cost_per_message: Optional[Decimal]
    last_used: Optional[datetime]
