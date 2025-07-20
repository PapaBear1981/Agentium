# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### System Management
- **Start System**: `docker-compose up -d` - Starts all Docker services
- **Test System**: `python scripts/test_system.py` - Comprehensive system tests (requires `pip install websockets httpx`)
- **Simple Test**: `python scripts/simple_test.py` - Basic functionality test

### Docker Operations
- **Start All Services**: `docker-compose up -d`
- **View Logs**: `docker-compose logs -f [service_name]`
- **Restart Services**: `docker-compose restart`
- **Stop System**: `docker-compose down`
- **Full Reset**: `docker-compose down -v` (removes volumes)
- **Rebuild Service**: `docker-compose build [service_name]`

### Health Checks
- **Frontend**: `curl http://localhost:8000/health`
- **Agent Service**: `curl http://localhost:8001/health` ✅ Working
- **Voice Service**: `curl http://localhost:8002/health` ✅ Working
- **Qdrant**: `curl http://localhost:6333/healthz` ⚠️ Note: uses `/healthz` not `/health`
- **Ollama**: `curl http://localhost:11434/api/tags`

### Task Processing
- **Process Task**: `curl -X POST http://localhost:8001/tasks/process -H "Content-Type: application/json" -d '{"content": "Hello", "session_id": "test"}'`

## Architecture Overview

This is a sophisticated multi-agent AI system built around Docker microservices:

### Core Services
1. **FastAPI WebSocket Frontend** (`service/frontend.py`, port 8000) - Real-time communication hub
2. **Agent Service** (`service/agent.py`, port 8001) - AutoGen-based multi-agent orchestration
3. **Voice Adapter** (`service/voice.py`, port 8002) - Speech-to-Text and Text-to-Speech processing

### Supporting Infrastructure
- **PostgreSQL** (port 5432) - Primary database with pgvector extension
- **Qdrant** (port 6333) - Vector database for RAG functionality
- **Ollama** (port 11434) - Local LLM serving
- **Redis** (port 6379) - Caching and session management

### Key Components
- **Multi-Agent System**: Uses AutoGen framework with 4 specialized agents (GPT-4o, Gemma2-7B, Gemini-2.5, Llama3.2-8B)
- **Voice Processing**: Multiple provider support (WhisperX, ElevenLabs, Coqui TTS, pyttsx3)
- **RAG System**: Document processing and retrieval using Qdrant and sentence transformers
- **MCP Integration**: Dynamic tool management with Smithery registry
- **Cost Tracking**: Real-time budget monitoring and alerts
- **Reflexion System**: Self-improvement capabilities through task analysis

## Service Structure

### Agent Service (`service/agent.py`)
- AutoGen-based agent orchestration
- Model provider abstraction (OpenRouter, Ollama)
- Task routing and execution
- MCP tool integration

### Frontend Service (`service/frontend.py`)
- WebSocket API for real-time communication
- CORS middleware configuration
- Session management
- Message routing between services

### Voice Service (`service/voice.py`)
- Abstract provider pattern for STT/TTS
- Multiple provider support with fallbacks
- Streaming audio processing
- Performance metrics tracking

### Models (`service/models/`)
- Pydantic models for all data structures
- Agent configurations and status
- WebSocket message types
- Voice processing types
- Database schemas

## Configuration

### Environment Variables (.env)
Key variables for development:
- `OPENROUTER_API_KEY` - For cloud models
- `ELEVENLABS_API_KEY` - For premium voice
- `STT_PROVIDER` - Speech-to-text provider (whisperx, elevenlabs, assemblyai)
- `TTS_PROVIDER` - Text-to-speech provider (coqui, elevenlabs, pyttsx3)
- `BUDGET_LIMIT` - Cost limit per session (USD)
- `MAX_TURNS` - Maximum conversation turns
- `LOG_LEVEL` - Logging level (INFO, DEBUG, WARNING)

### Docker Configuration
- Services defined in `docker-compose.yml`
- Separate Dockerfiles for each service in `service/` directory
- Health checks configured for all services
- Volume mounts for data persistence and development

## Testing

### Test Files
- `scripts/test_system.py` - Comprehensive system tests
- `scripts/simple_test.py` - Basic functionality tests
- `scripts/docker_test.py` - Docker-specific tests

### Test Coverage
- WebSocket communication
- HTTP API endpoints
- Voice processing workflows
- Agent system functionality
- Database operations
- Health checks

## Development Workflow

1. **Environment Setup**: Copy `.env.example` to `.env` and configure API keys
2. **Service Start**: Use `./scripts/start_system.sh` to start all services
3. **Verification**: Run `python scripts/test_system.py` to verify functionality
4. **Development**: Services auto-reload during development
5. **Debugging**: Use `docker-compose logs -f [service]` for troubleshooting

## Current Status (As of Implementation)

### ✅ Working Components
- **Agent Service**: Simplified implementation with OpenRouter integration (GPT-4o, Gemini)
- **Voice Service**: ElevenLabs STT/TTS integration working
- **FastAPI Frontend**: WebSocket server operational
- **Database**: PostgreSQL with pgvector extension
- **Vector DB**: Qdrant running (health endpoint is `/healthz`)
- **Local LLM**: Ollama with llama3.2:1b model

### ⚠️ Known Issues
1. **AutoGen Framework**: Original complex implementation had type annotation issues, replaced with simplified version
2. **RAG System**: Disabled due to sentence-transformers dependency conflicts  
3. **Qdrant Health**: Uses `/healthz` endpoint, not `/health`
4. **MCP Tools**: Not implemented in simplified version
5. **WebSocket Messages**: Some message types need frontend integration

### 🔧 Quick Fixes Applied
- Removed heavy ML dependencies (sentence-transformers, torch) for faster startup
- Added port mapping for agent service (8001:8001)
- Fixed Docker health checks to use available tools
- Simplified service dependencies to prevent circular waits

## Key Patterns

- **Async/Await**: All services use async Python patterns
- **Structured Logging**: Using structlog for JSON-formatted logs
- **Pydantic Models**: Type-safe data validation throughout
- **Health Checks**: All services implement health endpoints
- **Graceful Degradation**: Fallback providers for voice and LLM services
- **OpenRouter Integration**: Multi-model support via OpenRouter API

## Dependencies

Services use Python with these key frameworks:
- **FastAPI** - Web framework and WebSocket support
- **HTTPx** - Async HTTP client for OpenRouter
- **SQLAlchemy** - Database ORM with async support
- **Qdrant Client** - Vector database integration
- **WhisperX/ElevenLabs** - Voice processing
- **Structlog** - Structured logging

## Next Steps for Developers

1. **Re-enable RAG**: Add sentence-transformers back and fix import issues
2. **Restore AutoGen**: Fix type annotation issues in original agent.py
3. **Add MCP Tools**: Implement tool management system
4. **Frontend Integration**: Connect WebSocket message handlers
5. **Performance**: Add back GPU support and optimize models