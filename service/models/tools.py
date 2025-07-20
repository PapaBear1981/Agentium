"""
Tool models for MCP integration and dynamic tool management.

These models define the structure for tool installation, execution,
and management through the Smithery MCP registry.
"""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

class ToolStatus(str, Enum):
    AVAILABLE = "available"
    INSTALLING = "installing"
    INSTALLED = "installed"
    UPDATING = "updating"
    ERROR = "error"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"

class ToolCategory(str, Enum):
    WEB_SEARCH = "web_search"
    FILE_OPERATIONS = "file_operations"
    DATA_ANALYSIS = "data_analysis"
    API_INTEGRATION = "api_integration"
    SYSTEM_OPERATIONS = "system_operations"
    COMMUNICATION = "communication"
    PRODUCTIVITY = "productivity"
    DEVELOPMENT = "development"
    SECURITY = "security"
    CUSTOM = "custom"

class ToolExecutionStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"

class ToolSafetyLevel(str, Enum):
    SAFE = "safe"
    CAUTION = "caution"
    RESTRICTED = "restricted"
    DANGEROUS = "dangerous"

class ToolInstallRequest(BaseModel):
    """Request to install a new MCP tool."""
    tool_name: str
    version: Optional[str] = "latest"
    registry_url: Optional[str] = None
    force_reinstall: bool = False
    
    # Installation options
    install_dependencies: bool = True
    verify_signature: bool = True
    run_safety_scan: bool = True
    
    # Configuration
    config: Dict[str, Any] = Field(default_factory=dict)
    environment_variables: Dict[str, str] = Field(default_factory=dict)
    
    # Metadata
    requested_by: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolInstallResponse(BaseModel):
    """Response from tool installation."""
    tool_name: str
    version: str
    status: ToolStatus
    
    # Installation details
    install_id: UUID = Field(default_factory=lambda: UUID(int=0))
    installation_time_ms: int = 0
    
    # Results
    success: bool
    message: str
    error_details: Optional[Dict[str, Any]] = None
    
    # Safety information
    safety_score: Optional[int] = Field(None, ge=0, le=100)
    safety_level: Optional[ToolSafetyLevel] = None
    safety_warnings: List[str] = Field(default_factory=list)
    
    # Dependencies
    dependencies_installed: List[str] = Field(default_factory=list)
    dependencies_failed: List[str] = Field(default_factory=list)
    
    # Metadata
    installed_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    tool_name: str
    function_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    # Execution context
    session_id: Optional[UUID] = None
    agent_id: Optional[str] = None
    task_id: Optional[UUID] = None
    
    # Execution options
    timeout_seconds: int = 60
    max_retries: int = 3
    async_execution: bool = False
    
    # Security
    sandbox_mode: bool = True
    allowed_resources: List[str] = Field(default_factory=list)
    
    # Metadata
    execution_id: UUID = Field(default_factory=lambda: UUID(int=0))
    requested_by: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolExecutionResponse(BaseModel):
    """Response from tool execution."""
    execution_id: UUID
    tool_name: str
    function_name: str
    status: ToolExecutionStatus
    
    # Results
    result: Optional[Any] = None
    output: Optional[str] = None
    artifacts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Execution details
    execution_time_ms: int = 0
    memory_used_mb: Optional[float] = None
    cpu_time_ms: Optional[int] = None
    
    # Error handling
    error: Optional[str] = None
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    
    # Security
    security_violations: List[str] = Field(default_factory=list)
    resources_accessed: List[str] = Field(default_factory=list)
    
    # Metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolDefinition(BaseModel):
    """Definition of an available tool."""
    name: str
    version: str
    description: str
    category: ToolCategory
    
    # Tool information
    author: str
    license: str
    homepage: Optional[str] = None
    documentation_url: Optional[str] = None
    
    # Functions
    functions: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Requirements
    dependencies: List[str] = Field(default_factory=list)
    system_requirements: Dict[str, Any] = Field(default_factory=dict)
    
    # Safety and security
    safety_level: ToolSafetyLevel = ToolSafetyLevel.SAFE
    safety_score: int = Field(100, ge=0, le=100)
    permissions_required: List[str] = Field(default_factory=list)
    
    # Installation
    install_size_mb: Optional[float] = None
    install_time_estimate_seconds: Optional[int] = None
    
    # Usage statistics
    download_count: int = 0
    rating: Optional[float] = Field(None, ge=0.0, le=5.0)
    usage_count: int = 0
    
    # Metadata
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolRegistry(BaseModel):
    """Registry entry for an installed tool."""
    id: UUID = Field(default_factory=lambda: UUID(int=0))
    tool_name: str
    version: str
    status: ToolStatus
    
    # Installation details
    installed_at: datetime = Field(default_factory=datetime.utcnow)
    install_path: str
    config: Dict[str, Any] = Field(default_factory=dict)
    
    # Usage tracking
    usage_count: int = 0
    last_used: Optional[datetime] = None
    total_execution_time_ms: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # Performance metrics
    avg_execution_time_ms: float = 0.0
    success_rate: float = 0.0
    
    # Safety information
    safety_score: int = Field(100, ge=0, le=100)
    safety_violations: int = 0
    last_safety_check: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolSearchRequest(BaseModel):
    """Request to search for tools in the registry."""
    query: Optional[str] = None
    category: Optional[ToolCategory] = None
    tags: List[str] = Field(default_factory=list)
    
    # Filters
    min_rating: Optional[float] = None
    max_install_size_mb: Optional[float] = None
    safety_level: Optional[ToolSafetyLevel] = None
    
    # Sorting
    sort_by: str = "relevance"  # relevance, rating, downloads, updated
    sort_order: str = "desc"  # asc, desc
    
    # Pagination
    limit: int = Field(20, ge=1, le=100)
    offset: int = Field(0, ge=0)

class ToolSearchResponse(BaseModel):
    """Response from tool search."""
    tools: List[ToolDefinition]
    total_count: int
    query: Optional[str] = None
    filters_applied: Dict[str, Any] = Field(default_factory=dict)
    
    # Search metadata
    search_time_ms: int = 0
    suggestions: List[str] = Field(default_factory=list)

class ToolMetrics(BaseModel):
    """Metrics for tool usage and performance."""
    tool_name: str
    time_period_start: datetime
    time_period_end: datetime
    
    # Usage metrics
    execution_count: int = 0
    unique_users: int = 0
    total_execution_time_ms: int = 0
    avg_execution_time_ms: float = 0.0
    
    # Performance metrics
    success_count: int = 0
    failure_count: int = 0
    timeout_count: int = 0
    success_rate: float = 0.0
    
    # Resource usage
    total_memory_used_mb: float = 0.0
    avg_memory_used_mb: float = 0.0
    peak_memory_used_mb: float = 0.0
    
    # Error analysis
    error_types: Dict[str, int] = Field(default_factory=dict)
    most_common_error: Optional[str] = None
    
    # Security
    security_violations: int = 0
    safety_score_trend: List[float] = Field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolSystemStatus(BaseModel):
    """Overall status of the tool system."""
    total_tools_installed: int = 0
    tools_available: int = 0
    tools_error: int = 0
    tools_updating: int = 0
    
    # Performance
    active_executions: int = 0
    execution_queue_size: int = 0
    avg_execution_time_ms: float = 0.0
    
    # Safety
    safety_scan_enabled: bool = True
    last_safety_scan: Optional[datetime] = None
    tools_with_violations: int = 0
    
    # System health
    system_health: str = "healthy"  # healthy, degraded, unhealthy
    registry_connection: bool = True
    sandbox_available: bool = True
    
    # Metadata
    uptime_seconds: int = 0
    version: str = "1.0.0"
    last_updated: datetime = Field(default_factory=datetime.utcnow)

# Utility functions for tool management
def create_tool_install_request(
    tool_name: str,
    version: str = "latest",
    config: Optional[Dict[str, Any]] = None,
    **kwargs
) -> ToolInstallRequest:
    """Create a tool installation request."""
    return ToolInstallRequest(
        tool_name=tool_name,
        version=version,
        config=config or {},
        **kwargs
    )

def create_tool_execution_request(
    tool_name: str,
    function_name: str,
    parameters: Optional[Dict[str, Any]] = None,
    session_id: Optional[UUID] = None,
    **kwargs
) -> ToolExecutionRequest:
    """Create a tool execution request."""
    return ToolExecutionRequest(
        tool_name=tool_name,
        function_name=function_name,
        parameters=parameters or {},
        session_id=session_id,
        **kwargs
    )
