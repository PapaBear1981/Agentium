"""
Multi-Agent System Core for Jarvis AI System.

This module implements the AutoGen-based multi-agent orchestration system
with support for different LLM providers, tool integration, and voice processing.
"""

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID, uuid4

import structlog
from autogen_core import (
    AgentId, MessageContext, RoutedAgent, SingleThreadedAgentRuntime, 
    message_handler, default_subscription, DefaultTopicId
)
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage, AssistantMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient
try:
    from autogen_ext.models.ollama import OllamaChatCompletionClient
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    print("Warning: Ollama client not available, using OpenAI only")

from models.agents import (
    AgentConfig, TaskRequest, TaskResponse, AgentStatus, TaskStatus,
    ModelProvider, AgentRole, TaskPriority
)
from models.websocket import (
    WebSocketMessage, AgentResponseMessage, ToolExecutionMessage,
    create_agent_response_message, create_error_message
)
from models.voice import STTRequest, TTSRequest, VoiceConfig
from mcp_integration import MCPManager
from voice import VoiceProcessor
# RAG system will be imported later if available
RAG_AVAILABLE = True

logger = structlog.get_logger(__name__)

# Message types for agent communication
@dataclass
class UserTask:
    """Task from user to be processed by agents."""
    task_id: UUID
    session_id: UUID
    content: str
    context: Dict[str, Any]
    priority: TaskPriority = TaskPriority.MEDIUM

@dataclass
class AgentTask:
    """Task assigned to a specific agent."""
    task_id: UUID
    session_id: UUID
    agent_id: str
    content: str
    context: Dict[str, Any]
    previous_results: List[str] = None

@dataclass
class AgentResult:
    """Result from agent task execution."""
    task_id: UUID
    agent_id: str
    result: str
    success: bool
    tokens_used: int = 0
    cost: float = 0.0
    processing_time_ms: int = 0
    metadata: Dict[str, Any] = None

@dataclass
class ToolExecutionRequest:
    """Request to execute a tool."""
    tool_name: str
    function_name: str
    parameters: Dict[str, Any]
    agent_id: str
    session_id: UUID

@dataclass
class VoiceProcessingRequest:
    """Request for voice processing."""
    session_id: UUID
    operation: str  # 'stt' or 'tts'
    data: str  # audio data or text
    config: Dict[str, Any] = None

class JarvisAgent(RoutedAgent):
    """Base agent class for the Jarvis system."""
    
    def __init__(
        self,
        config: AgentConfig,
        model_client: ChatCompletionClient,
        mcp_manager: Optional[MCPManager] = None,
        voice_processor: Optional[VoiceProcessor] = None,
        rag_system: Optional['RAGSystem'] = None
    ):
        super().__init__(config.description)
        self.config = config
        self.model_client = model_client
        self.mcp_manager = mcp_manager
        self.voice_processor = voice_processor
        self.rag_system = rag_system
        
        # Agent state
        self.current_task: Optional[UUID] = None
        self.task_history: List[Dict[str, Any]] = []
        self.performance_metrics = {
            "tasks_completed": 0,
            "tasks_failed": 0,
            "total_tokens": 0,
            "total_cost": 0.0,
            "avg_response_time": 0.0
        }
        
        # System messages
        self.system_messages = [SystemMessage(content=config.system_message)]
        
        logger.info(f"Initialized agent: {config.id}", 
                   model=config.model_name, 
                   provider=config.model_provider.value)
    
    @message_handler
    async def handle_user_task(self, message: UserTask, ctx: MessageContext) -> AgentResult:
        """Handle a task from the user."""
        start_time = time.time()
        self.current_task = message.task_id
        
        try:
            logger.info(f"Agent {self.config.id} processing task", 
                       task_id=str(message.task_id),
                       content=message.content[:100])
            
            # Prepare context
            context_info = await self._prepare_context(message)
            
            # Create messages for the model
            messages = self.system_messages.copy()
            
            # Add context if available
            if context_info:
                context_message = SystemMessage(content=f"Context: {context_info}")
                messages.append(context_message)
            
            # Add user message
            messages.append(UserMessage(content=message.content, source="user"))
            
            # Get model response
            model_result = await self.model_client.create(messages)
            
            # Process tools if needed
            if hasattr(model_result, 'tool_calls') and model_result.tool_calls:
                tool_results = await self._execute_tools(model_result.tool_calls, message.session_id)
                # Add tool results to context and get final response
                tool_context = f"Tool results: {json.dumps(tool_results)}"
                messages.append(AssistantMessage(content=model_result.content, source=self.config.id))
                messages.append(SystemMessage(content=tool_context))
                model_result = await self.model_client.create(messages)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # Update metrics
            self.performance_metrics["tasks_completed"] += 1
            self.performance_metrics["total_tokens"] += getattr(model_result, 'usage', {}).get('total_tokens', 0)
            self.performance_metrics["avg_response_time"] = (
                (self.performance_metrics["avg_response_time"] * (self.performance_metrics["tasks_completed"] - 1) + processing_time) 
                / self.performance_metrics["tasks_completed"]
            )
            
            # Store task in history
            self.task_history.append({
                "task_id": str(message.task_id),
                "content": message.content,
                "result": model_result.content,
                "timestamp": time.time(),
                "processing_time_ms": processing_time
            })
            
            result = AgentResult(
                task_id=message.task_id,
                agent_id=self.config.id,
                result=model_result.content,
                success=True,
                tokens_used=getattr(model_result, 'usage', {}).get('total_tokens', 0),
                processing_time_ms=processing_time,
                metadata={"model": self.config.model_name}
            )
            
            logger.info(f"Agent {self.config.id} completed task",
                       task_id=str(message.task_id),
                       tokens=result.tokens_used,
                       time_ms=processing_time)
            
            return result
            
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            self.performance_metrics["tasks_failed"] += 1
            
            logger.error(f"Agent {self.config.id} task failed",
                        task_id=str(message.task_id),
                        error=str(e))
            
            return AgentResult(
                task_id=message.task_id,
                agent_id=self.config.id,
                result=f"Task failed: {str(e)}",
                success=False,
                processing_time_ms=processing_time,
                metadata={"error": str(e)}
            )
        finally:
            self.current_task = None
    
    async def _prepare_context(self, message: UserTask) -> str:
        """Prepare context for the task using RAG if available."""
        context_parts = []
        
        # Add RAG context if available
        if self.rag_system and message.content:
            try:
                search_results, rag_context = await self.rag_system.search_and_retrieve(
                    query=message.content,
                    limit=3,
                    score_threshold=0.7
                )
                if rag_context:
                    context_parts.append(f"Relevant information: {rag_context}")
            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {e}")
        
        # Add session context
        if message.context:
            context_parts.append(f"Session context: {json.dumps(message.context)}")
        
        return "\n\n".join(context_parts)
    
    async def _execute_tools(self, tool_calls: List[Dict[str, Any]], session_id: UUID) -> List[Dict[str, Any]]:
        """Execute tool calls using MCP manager."""
        results = []
        
        if not self.mcp_manager:
            return results
        
        for tool_call in tool_calls:
            try:
                tool_name = tool_call.get("function", {}).get("name")
                parameters = json.loads(tool_call.get("function", {}).get("arguments", "{}"))
                
                response = await self.mcp_manager.execute_tool(
                    tool_name=tool_name,
                    function_name="execute",  # Default function name
                    parameters=parameters,
                    session_id=session_id,
                    agent_id=self.config.id
                )
                
                results.append({
                    "tool": tool_name,
                    "success": response.status.value == "completed",
                    "result": response.result,
                    "error": response.error
                })
                
            except Exception as e:
                logger.error(f"Tool execution failed: {e}")
                results.append({
                    "tool": tool_call.get("function", {}).get("name", "unknown"),
                    "success": False,
                    "error": str(e)
                })
        
        return results
    
    def get_status(self) -> AgentStatus:
        """Get current agent status."""
        status = "active" if self.current_task else "idle"
        
        return AgentStatus(
            agent_id=self.config.id,
            name=self.config.name,
            status=status,
            current_task_id=self.current_task,
            tasks_completed=self.performance_metrics["tasks_completed"],
            tasks_failed=self.performance_metrics["tasks_failed"],
            total_tokens_used=self.performance_metrics["total_tokens"],
            total_cost=self.performance_metrics["total_cost"],
            average_response_time_ms=self.performance_metrics["avg_response_time"]
        )

class ManagerAgent(RoutedAgent):
    """Manager agent that orchestrates tasks and delegates to specialist agents."""
    
    def __init__(
        self,
        agents: Dict[str, JarvisAgent],
        mcp_manager: MCPManager,
        voice_processor: VoiceProcessor,
        rag_system: 'RAGSystem'
    ):
        super().__init__("Manager Agent - Orchestrates tasks and delegates to specialist agents")
        self.agents = agents
        self.mcp_manager = mcp_manager
        self.voice_processor = voice_processor
        self.rag_system = rag_system
        
        # Manager state
        self.active_sessions: Dict[UUID, Dict[str, Any]] = {}
        self.task_queue: List[UserTask] = []
        
        logger.info("Initialized ManagerAgent", agents=list(agents.keys()))
    
    @message_handler
    async def handle_user_task(self, message: UserTask, ctx: MessageContext) -> AgentResult:
        """Handle user task and delegate to appropriate agent."""
        try:
            logger.info("ManagerAgent received task", 
                       task_id=str(message.task_id),
                       session_id=str(message.session_id))
            
            # Initialize session if needed
            if message.session_id not in self.active_sessions:
                self.active_sessions[message.session_id] = {
                    "created_at": time.time(),
                    "task_count": 0,
                    "total_cost": 0.0
                }
            
            session = self.active_sessions[message.session_id]
            session["task_count"] += 1
            
            # Select appropriate agent
            selected_agent = await self._select_agent(message)
            
            # Delegate task to selected agent
            result = await selected_agent.handle_user_task(message, ctx)
            
            # Update session metrics
            session["total_cost"] += result.cost
            
            logger.info("ManagerAgent completed task delegation",
                       task_id=str(message.task_id),
                       selected_agent=selected_agent.config.id,
                       success=result.success)
            
            return result
            
        except Exception as e:
            logger.error("ManagerAgent task delegation failed", error=str(e))
            return AgentResult(
                task_id=message.task_id,
                agent_id="manager",
                result=f"Task delegation failed: {str(e)}",
                success=False,
                metadata={"error": str(e)}
            )
    
    async def _select_agent(self, message: UserTask) -> JarvisAgent:
        """Select the most appropriate agent for the task."""
        # Simple selection logic - can be enhanced with ML-based routing
        content_lower = message.content.lower()
        
        # Check for specific keywords to route to specialized agents
        if any(keyword in content_lower for keyword in ["code", "program", "script", "debug"]):
            return self.agents.get("agent1_openrouter_gpt40", list(self.agents.values())[0])
        elif any(keyword in content_lower for keyword in ["search", "find", "lookup", "research"]):
            return self.agents.get("agent3_openrouter_gemini25", list(self.agents.values())[0])
        elif any(keyword in content_lower for keyword in ["analyze", "data", "calculate"]):
            return self.agents.get("agent2_ollama_gemma3_7b", list(self.agents.values())[0])
        else:
            # Default to the first available agent
            return list(self.agents.values())[0]
    
    @message_handler
    async def handle_voice_request(self, message: VoiceProcessingRequest, ctx: MessageContext) -> Dict[str, Any]:
        """Handle voice processing requests."""
        try:
            if message.operation == "stt":
                # Speech to text
                stt_request = STTRequest(
                    audio_data=message.data,
                    session_id=str(message.session_id)
                )
                response = await self.voice_processor.transcribe(stt_request)
                return {
                    "success": response.success,
                    "text": response.text,
                    "confidence": response.confidence,
                    "processing_time_ms": response.processing_time_ms
                }
            
            elif message.operation == "tts":
                # Text to speech
                tts_request = TTSRequest(
                    text=message.data,
                    session_id=str(message.session_id)
                )
                response = await self.voice_processor.synthesize(tts_request)
                return {
                    "success": response.success,
                    "audio_data": response.audio_data,
                    "duration_ms": response.duration_ms,
                    "processing_time_ms": response.processing_time_ms
                }
            
            else:
                raise ValueError(f"Unknown voice operation: {message.operation}")
                
        except Exception as e:
            logger.error("Voice processing failed", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        agent_statuses = {agent_id: agent.get_status() for agent_id, agent in self.agents.items()}
        
        return {
            "manager_status": "active",
            "active_sessions": len(self.active_sessions),
            "agents": agent_statuses,
            "task_queue_size": len(self.task_queue),
            "total_tasks_processed": sum(status.tasks_completed for status in agent_statuses.values()),
            "system_uptime": time.time()  # Would track actual uptime
        }

class AgentOrchestrator:
    """Main orchestrator for the multi-agent system."""

    def __init__(self):
        self.runtime: Optional[SingleThreadedAgentRuntime] = None
        self.agents: Dict[str, JarvisAgent] = {}
        self.manager_agent: Optional[ManagerAgent] = None
        self.mcp_manager: Optional[MCPManager] = None
        self.voice_processor: Optional[VoiceProcessor] = None
        self.rag_system: Optional['RAGSystem'] = None
        self.model_clients: Dict[str, ChatCompletionClient] = {}

        # System state
        self.is_initialized = False
        self.startup_time = time.time()

        logger.info("AgentOrchestrator created")

    async def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the agent orchestrator with configuration."""
        try:
            logger.info("Initializing AgentOrchestrator")

            # Initialize runtime
            self.runtime = SingleThreadedAgentRuntime()

            # Initialize model clients
            await self._initialize_model_clients(config)

            # Initialize supporting systems
            await self._initialize_supporting_systems(config)

            # Initialize agents
            await self._initialize_agents(config)

            # Initialize manager agent
            await self._initialize_manager_agent()

            # Register agents with runtime
            await self._register_agents()

            # Start runtime
            self.runtime.start()

            self.is_initialized = True
            logger.info("AgentOrchestrator initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize AgentOrchestrator: {e}")
            raise

    async def _initialize_model_clients(self, config: Dict[str, Any]) -> None:
        """Initialize model clients for different providers."""
        # OpenRouter clients
        openrouter_api_key = config.get("openrouter_api_key")
        if openrouter_api_key:
            self.model_clients["gpt-4o"] = OpenAIChatCompletionClient(
                model="gpt-4o",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key
            )
            self.model_clients["gemini-2.5-flash"] = OpenAIChatCompletionClient(
                model="gemini-2.5-flash",
                base_url="https://openrouter.ai/api/v1",
                api_key=openrouter_api_key
            )

        # Ollama clients
        if OLLAMA_AVAILABLE:
            ollama_url = config.get("ollama_url", "http://localhost:11434")
            try:
                self.model_clients["gemma2:7b"] = OllamaChatCompletionClient(
                    model="gemma2:7b",
                    base_url=ollama_url
                )
                self.model_clients["llama3.2:8b"] = OllamaChatCompletionClient(
                    model="llama3.2:8b",
                    base_url=ollama_url
                )
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama clients: {e}")
        else:
            logger.warning("Ollama not available, skipping local model clients")

        logger.info("Model clients initialized", clients=list(self.model_clients.keys()))

    async def _initialize_supporting_systems(self, config: Dict[str, Any]) -> None:
        """Initialize MCP, voice, and RAG systems."""
        # Initialize MCP Manager
        self.mcp_manager = MCPManager(
            registry_url=config.get("smithery_registry_url", "https://smithery.ai/api/v1"),
            tools_dir=Path(config.get("mcp_tools_dir", "./mcp_tools"))
        )
        await self.mcp_manager.initialize()

        # Initialize Voice Processor
        voice_config = VoiceConfig(
            stt_provider=config.get("stt_provider", "whisperx"),
            tts_provider=config.get("tts_provider", "coqui"),
            provider_config={
                "elevenlabs_api_key": config.get("elevenlabs_api_key"),
                "use_gpu": config.get("use_gpu", False)
            }
        )
        self.voice_processor = VoiceProcessor(voice_config)

        # Initialize RAG System
        try:
            from retrieval import RAGSystem, QdrantVectorStore, DocumentProcessor
            vector_store = QdrantVectorStore(
                url=config.get("qdrant_url", "http://localhost:6333"),
                collection_name="jarvis_documents"
            )
            document_processor = DocumentProcessor()
            self.rag_system = RAGSystem(vector_store, document_processor)
            logger.info("RAG system initialized successfully")
        except ImportError as e:
            self.rag_system = None
            logger.warning(f"RAG system disabled due to missing dependencies: {e}")

        logger.info("Supporting systems initialized")

    async def _initialize_agents(self, config: Dict[str, Any]) -> None:
        """Initialize individual agents."""
        agent_configs = [
            AgentConfig(
                id="agent1_openrouter_gpt40",
                name="GPT-4o Reasoning Agent",
                description="Advanced reasoning and problem-solving agent using GPT-4o",
                role=AgentRole.SPECIALIST,
                model_name="gpt-4o",
                model_provider=ModelProvider.OPENROUTER,
                system_message="You are an advanced AI assistant with exceptional reasoning capabilities. You excel at complex problem-solving, analysis, and providing detailed explanations. Always think step-by-step and provide clear, well-structured responses."
            ),
            AgentConfig(
                id="agent2_ollama_gemma3_7b",
                name="Gemma2 Local Agent",
                description="Local processing agent using Gemma2 7B model",
                role=AgentRole.EXECUTOR,
                model_name="gemma2:7b",
                model_provider=ModelProvider.OLLAMA,
                system_message="You are a helpful AI assistant running locally. You provide quick, efficient responses and can handle a variety of tasks. Focus on being concise while maintaining accuracy."
            ),
            AgentConfig(
                id="agent3_openrouter_gemini25",
                name="Gemini Research Agent",
                description="Research and information gathering agent using Gemini 2.5",
                role=AgentRole.RESEARCHER,
                model_name="gemini-2.5-flash",
                model_provider=ModelProvider.OPENROUTER,
                system_message="You are a research specialist with access to vast knowledge. You excel at finding information, conducting analysis, and providing comprehensive research results. Always cite sources when possible."
            ),
            AgentConfig(
                id="agent4_ollama_llama4_32b",
                name="Llama Local Agent",
                description="Local high-capacity agent using Llama 3.2 8B model",
                role=AgentRole.CRITIC,
                model_name="llama3.2:8b",
                model_provider=ModelProvider.OLLAMA,
                system_message="You are a critical thinking specialist. You review, analyze, and provide constructive feedback on ideas, solutions, and content. You help improve quality through thoughtful critique."
            )
        ]

        for agent_config in agent_configs:
            if agent_config.model_name in self.model_clients:
                agent = JarvisAgent(
                    config=agent_config,
                    model_client=self.model_clients[agent_config.model_name],
                    mcp_manager=self.mcp_manager,
                    voice_processor=self.voice_processor,
                    rag_system=self.rag_system
                )
                self.agents[agent_config.id] = agent
                logger.info(f"Created agent: {agent_config.id}")
            else:
                logger.warning(f"Model client not available for agent: {agent_config.id}")

        logger.info("Agents initialized", count=len(self.agents))

    async def _initialize_manager_agent(self) -> None:
        """Initialize the manager agent."""
        self.manager_agent = ManagerAgent(
            agents=self.agents,
            mcp_manager=self.mcp_manager,
            voice_processor=self.voice_processor,
            rag_system=self.rag_system
        )
        logger.info("Manager agent initialized")

    async def _register_agents(self) -> None:
        """Register all agents with the runtime."""
        # Register individual agents
        for agent_id, agent in self.agents.items():
            await JarvisAgent.register(
                self.runtime,
                agent_id,
                lambda a=agent: a
            )

        # Register manager agent
        await ManagerAgent.register(
            self.runtime,
            "manager",
            lambda: self.manager_agent
        )

        logger.info("All agents registered with runtime")

    async def process_user_task(
        self,
        content: str,
        session_id: UUID,
        context: Optional[Dict[str, Any]] = None
    ) -> AgentResult:
        """Process a user task through the agent system."""
        if not self.is_initialized:
            raise RuntimeError("AgentOrchestrator not initialized")

        task = UserTask(
            task_id=uuid4(),
            session_id=session_id,
            content=content,
            context=context or {},
            priority=TaskPriority.MEDIUM
        )

        # Send task to manager agent
        result = await self.runtime.send_message(
            task,
            AgentId("manager", "default")
        )

        return result

    async def process_voice_request(
        self,
        operation: str,
        data: str,
        session_id: UUID,
        config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Process a voice request (STT or TTS)."""
        if not self.is_initialized:
            raise RuntimeError("AgentOrchestrator not initialized")

        voice_request = VoiceProcessingRequest(
            session_id=session_id,
            operation=operation,
            data=data,
            config=config or {}
        )

        result = await self.runtime.send_message(
            voice_request,
            AgentId("manager", "default")
        )

        return result

    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        if not self.manager_agent:
            return {"status": "not_initialized"}

        status = self.manager_agent.get_system_status()

        # Add orchestrator-level information
        status.update({
            "orchestrator_initialized": self.is_initialized,
            "startup_time": self.startup_time,
            "uptime_seconds": int(time.time() - self.startup_time),
            "model_clients": list(self.model_clients.keys()),
            "supporting_systems": {
                "mcp_manager": self.mcp_manager is not None,
                "voice_processor": self.voice_processor is not None,
                "rag_system": self.rag_system is not None
            }
        })

        return status

    async def shutdown(self) -> None:
        """Shutdown the agent orchestrator."""
        logger.info("Shutting down AgentOrchestrator")

        if self.runtime:
            await self.runtime.stop()

        # Close model clients
        for client in self.model_clients.values():
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing model client: {e}")

        self.is_initialized = False
        logger.info("AgentOrchestrator shutdown complete")
