"""
Agent models for multi-agent system configuration and communication.

These models define the structure for agent configuration, task requests,
and responses in the AutoGen-based multi-agent system.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

class ModelProvider(str, Enum):
    OPENROUTER = "openrouter"
    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

class AgentRole(str, Enum):
    MANAGER = "manager"
    SPECIALIST = "specialist"
    CRITIC = "critic"
    EXECUTOR = "executor"
    RESEARCHER = "researcher"

class TaskStatus(str, Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class AgentConfig(BaseModel):
    """Configuration for an individual agent."""
    id: str
    name: str
    description: str
    role: AgentRole
    model_name: str
    model_provider: ModelProvider
    system_message: str
    
    # Model parameters
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(2048, ge=1, le=8192)
    top_p: float = Field(1.0, ge=0.0, le=1.0)
    frequency_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    presence_penalty: float = Field(0.0, ge=-2.0, le=2.0)
    
    # Agent behavior
    max_consecutive_auto_reply: int = Field(3, ge=1, le=10)
    human_input_mode: str = "NEVER"  # NEVER, TERMINATE, ALWAYS
    code_execution_config: Optional[Dict[str, Any]] = None
    
    # Tools and capabilities
    tools: List[str] = Field(default_factory=list)
    tool_choice: str = "auto"  # auto, none, or specific tool name
    
    # Communication settings
    handoff_targets: List[str] = Field(default_factory=list)
    can_delegate: bool = True
    delegation_rules: Dict[str, Any] = Field(default_factory=dict)
    
    # Performance settings
    timeout_seconds: int = 60
    retry_attempts: int = 3
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TaskRequest(BaseModel):
    """Request for an agent to perform a task."""
    task_id: UUID = Field(default_factory=lambda: UUID(int=0))
    session_id: UUID
    requester_id: Optional[str] = None  # Agent ID or "user"
    assigned_agent_id: Optional[str] = None
    
    # Task details
    title: str
    description: str
    instructions: str
    priority: TaskPriority = TaskPriority.MEDIUM
    
    # Context and data
    context: Dict[str, Any] = Field(default_factory=dict)
    input_data: Optional[Any] = None
    expected_output_format: Optional[str] = None
    
    # Constraints
    max_turns: int = 5
    timeout_seconds: int = 300
    budget_limit: Optional[Decimal] = None
    
    # Dependencies
    depends_on: List[UUID] = Field(default_factory=list)
    blocks: List[UUID] = Field(default_factory=list)
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    deadline: Optional[datetime] = None

class TaskResponse(BaseModel):
    """Response from an agent after completing a task."""
    task_id: UUID
    agent_id: str
    status: TaskStatus
    
    # Results
    result: Optional[Any] = None
    output_text: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Execution details
    turns_used: int = 0
    tokens_used: int = 0
    cost: Decimal = Decimal("0.00")
    processing_time_ms: int = 0
    
    # Quality metrics
    confidence_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    
    # Error handling
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    
    # Communication
    messages: List[Dict[str, Any]] = Field(default_factory=list)
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: datetime = Field(default_factory=datetime.utcnow)

class AgentStatus(BaseModel):
    """Current status of an agent."""
    agent_id: str
    name: str
    status: str  # active, idle, busy, error, maintenance
    current_task_id: Optional[UUID] = None
    
    # Performance metrics
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_tokens_used: int = 0
    total_cost: Decimal = Decimal("0.00")
    average_response_time_ms: float = 0.0
    
    # Resource usage
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    
    # Health
    last_heartbeat: datetime = Field(default_factory=datetime.utcnow)
    error_count: int = 0
    last_error: Optional[str] = None
    
    # Metadata
    uptime_seconds: int = 0
    version: str = "1.0.0"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentCommunication(BaseModel):
    """Message between agents."""
    message_id: UUID = Field(default_factory=lambda: UUID(int=0))
    from_agent_id: str
    to_agent_id: str
    message_type: str  # request, response, notification, handoff
    
    # Content
    subject: Optional[str] = None
    content: str
    data: Optional[Dict[str, Any]] = None
    
    # Context
    task_id: Optional[UUID] = None
    session_id: Optional[UUID] = None
    thread_id: Optional[str] = None
    
    # Metadata
    priority: TaskPriority = TaskPriority.MEDIUM
    requires_response: bool = False
    response_timeout_seconds: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AgentTeam(BaseModel):
    """Configuration for a team of agents."""
    team_id: str
    name: str
    description: str
    
    # Team composition
    agents: List[str]  # Agent IDs
    manager_agent_id: Optional[str] = None
    
    # Team behavior
    collaboration_mode: str = "sequential"  # sequential, parallel, hierarchical
    communication_protocol: str = "broadcast"  # broadcast, direct, hierarchical
    
    # Task distribution
    load_balancing: bool = True
    specialization_routing: bool = True
    
    # Performance
    max_concurrent_tasks: int = 5
    task_timeout_seconds: int = 600
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class AgentPerformanceMetrics(BaseModel):
    """Performance metrics for an agent."""
    agent_id: str
    time_period_start: datetime
    time_period_end: datetime
    
    # Task metrics
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    success_rate: float = 0.0
    
    # Performance metrics
    avg_response_time_ms: float = 0.0
    avg_tokens_per_task: float = 0.0
    avg_cost_per_task: Decimal = Decimal("0.00")
    
    # Quality metrics
    avg_confidence_score: float = 0.0
    avg_quality_score: float = 0.0
    user_satisfaction_score: Optional[float] = None
    
    # Resource metrics
    total_tokens_used: int = 0
    total_cost: Decimal = Decimal("0.00")
    peak_memory_usage_mb: Optional[float] = None
    avg_cpu_usage_percent: Optional[float] = None
    
    # Error metrics
    error_count: int = 0
    timeout_count: int = 0
    retry_count: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

# Utility functions for agent management
def create_agent_config(
    id: str,
    name: str,
    description: str,
    role: AgentRole,
    model_name: str,
    model_provider: ModelProvider,
    system_message: str,
    **kwargs
) -> AgentConfig:
    """Create an agent configuration."""
    return AgentConfig(
        id=id,
        name=name,
        description=description,
        role=role,
        model_name=model_name,
        model_provider=model_provider,
        system_message=system_message,
        **kwargs
    )

def create_task_request(
    title: str,
    description: str,
    instructions: str,
    session_id: UUID,
    **kwargs
) -> TaskRequest:
    """Create a task request."""
    return TaskRequest(
        title=title,
        description=description,
        instructions=instructions,
        session_id=session_id,
        **kwargs
    )
