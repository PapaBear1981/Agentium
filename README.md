# 🤖 Agentium - Multi-Agent AI System

**A sophisticated, voice-enabled multi-agent AI system with real-time communication and dynamic tool management.**

> **Status**: Core functionality operational (70% test success rate) - Ready for development and enhancement

## 🌟 Features

### 🎤 Voice Processing
- **Speech-to-Text**: ElevenLabs, WhisperX support  
- **Text-to-Speech**: ElevenLabs, Coqui TTS, pyttsx3 support
- **Real-time Processing**: Streaming audio with WebSocket integration
- **Multiple Providers**: Fallback and quality options

### 🤖 Multi-Agent System  
- **OpenRouter Integration**: GPT-4o, Gemini-2.5 models
- **Local LLM Support**: Ollama with Llama3.2-8B
- **Smart Agent Selection**: Content-based routing to appropriate models
- **Simplified Architecture**: Fast startup, reliable performance

### 🌐 Real-time Communication
- **WebSocket API**: Bi-directional real-time communication
- **Voice Streaming**: Live audio input/output  
- **Session Management**: Multi-user session handling
- **RESTful APIs**: Standard HTTP endpoints for integration

### 🔍 Infrastructure Ready
- **PostgreSQL**: Database with pgvector extension for embeddings
- **Qdrant**: Vector database for semantic search
- **Redis**: Caching and session management
- **Docker**: Containerized microservices architecture

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- 8GB+ RAM (16GB recommended)
- OpenRouter API key (for GPT-4o/Gemini access)
- ElevenLabs API key (optional, for premium voice)

### 1. Clone and Setup
```bash
git clone https://github.com/PapaBear1981/Agentium.git
cd Agentium
cp .env.example .env
```

### 2. Configure Environment
Edit `.env` file with your API keys:
```bash
# Required for cloud models
OPENROUTER_API_KEY=your_openrouter_key_here

# Optional for premium voice
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# Voice providers
STT_PROVIDER=elevenlabs
TTS_PROVIDER=elevenlabs

# Budget limit per session (USD)  
BUDGET_LIMIT=100.00
```

### 3. Start the System
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps
```

### 4. Verify Installation
```bash
# Install test dependencies
pip install websockets httpx

# Run comprehensive tests
python scripts/test_system.py
```

## 📡 API Endpoints

### Core Services
- **FastAPI Frontend**: `http://localhost:8000` - WebSocket and HTTP API
- **Agent Service**: `http://localhost:8001` - AI task processing  
- **Voice Service**: `http://localhost:8002` - STT/TTS processing

### Health Checks
```bash
curl http://localhost:8000/health  # Frontend
curl http://localhost:8001/health  # Agents  
curl http://localhost:8002/health  # Voice
curl http://localhost:6333/healthz # Qdrant (note: /healthz not /health)
```

### Task Processing
```bash
# Process a task with AI
curl -X POST http://localhost:8001/tasks/process \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Explain quantum computing in simple terms",
    "session_id": "my-session"
  }'
```

### Voice Processing
```bash
# Text-to-speech
curl -X POST http://localhost:8002/tts \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Hello, this is Agentium speaking",
    "session_id": "my-session"
  }'
```

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Voice         │    │   Agent         │
│   (WebSocket)   │◄──►│   Service       │◄──►│   Service       │
│   Port: 8000    │    │   Port: 8002    │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │    │     Qdrant      │    │     Ollama      │
│   (Database)    │    │   (Vectors)     │    │   (Local LLM)   │
│   Port: 5432    │    │   Port: 6333    │    │   Port: 11434   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 💬 Usage Examples

### WebSocket Communication
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/my-session');

// Send text message
ws.send(JSON.stringify({
  type: 'text_input',
  data: {
    message: 'Hello Agentium, help me with coding',
    context: {}
  }
}));

// Handle responses
ws.onmessage = (event) => {
  const response = JSON.parse(event.data);
  console.log('AI Response:', response);
};
```

### Python Integration
```python
import httpx
import asyncio

async def chat_with_agentium(message):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8001/tasks/process",
            json={
                "content": message,
                "session_id": "python-session"
            }
        )
        return response.json()

# Usage
result = asyncio.run(chat_with_agentium("What's the weather like?"))
print(f"Agent: {result['content']}")
```

## 🔧 Development

### Project Structure
```
Agentium/
├── service/                 # Core services
│   ├── models/             # Pydantic models
│   ├── simple_agent_service.py  # Current working agent implementation
│   ├── agent.py            # Original AutoGen implementation (needs fixes)
│   ├── voice.py            # Voice processing
│   ├── frontend.py         # WebSocket API
│   └── requirements-*.txt  # Service dependencies
├── scripts/                # Utility scripts
│   ├── test_system.py     # Comprehensive tests
│   └── simple_test.py     # Basic functionality tests
├── data/docs/             # RAG documents (when enabled)
├── logs/                  # Application logs
├── docker-compose.yml     # Service orchestration
└── CLAUDE.md             # Developer guidance
```

### Running Tests
```bash
# Comprehensive system tests
python scripts/test_system.py

# Expected: ~70% pass rate (14/20 tests)
# Core functionality: ✅ Agent processing, Voice I/O, WebSocket
# Known issues: Qdrant health endpoint, some WebSocket message types
```

### Development Workflow
1. **Start Services**: `docker-compose up -d`
2. **View Logs**: `docker-compose logs -f [service_name]`
3. **Make Changes**: Edit code in `service/` directory
4. **Rebuild**: `docker-compose build [service_name]`
5. **Test**: `python scripts/test_system.py`

## 🎯 Current Status

### ✅ Working Features
- **Multi-Agent Processing**: GPT-4o and Gemini via OpenRouter
- **Voice I/O**: ElevenLabs STT/TTS integration
- **Real-time Communication**: WebSocket server
- **Database**: PostgreSQL with pgvector
- **Vector Search**: Qdrant operational
- **Local LLM**: Ollama with Llama models

### 🔄 In Development
- **RAG System**: Document processing and retrieval (dependencies disabled)
- **AutoGen Integration**: Complex multi-agent orchestration (type issues)
- **MCP Tools**: Dynamic tool management
- **Frontend UI**: Web interface for interactions

### 📊 Test Results
```
Total Tests: 20
Passed: 14 ✅  
Failed: 6 ❌
Success Rate: 70%

✅ Working: Agent processing, Voice I/O, Health checks, WebSocket
❌ Known Issues: Qdrant health endpoint, some message types
```

## 🔒 Security & Configuration

### Environment Variables
Key configuration options in `.env`:
- `OPENROUTER_API_KEY` - Required for GPT-4o/Gemini
- `ELEVENLABS_API_KEY` - Optional for premium voice
- `BUDGET_LIMIT` - Cost protection (default: $100)
- `STT_PROVIDER` / `TTS_PROVIDER` - Voice service configuration

### API Key Management
- Secure environment variable handling
- No keys logged or exposed in responses
- Budget controls to prevent runaway costs

## 🚨 Troubleshooting

### Common Issues

**Services won't start:**
```bash
# Check Docker status
docker info
docker-compose logs

# Restart specific service
docker-compose restart [service_name]
```

**Agent not responding:**
```bash
# Check if port is exposed
curl http://localhost:8001/health

# View agent logs
docker-compose logs agent_service
```

**Voice processing fails:**
```bash
# Verify ElevenLabs key
curl http://localhost:8002/providers

# Check voice service logs  
docker-compose logs voice_adapter
```

**High costs:**
- Monitor usage: `curl http://localhost:8001/metrics`
- Check budget settings in `.env`
- Consider using local models for development

## 🛣️ Roadmap

### Next Sprint
1. **Fix AutoGen Integration** - Resolve type annotation issues
2. **Re-enable RAG** - Add sentence-transformers back  
3. **Complete WebSocket Handlers** - Full message type support
4. **Add Frontend UI** - Web interface for interactions

### Future Enhancements
- **GPU Acceleration** - Enable CUDA support for local models
- **Advanced Tool Management** - MCP integration with Smithery
- **Performance Optimization** - Caching and response times
- **Monitoring Dashboard** - Real-time system metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes and test: `python scripts/test_system.py`
4. Commit changes: `git commit -m 'Add amazing feature'`
5. Push to branch: `git push origin feature/amazing-feature`
6. Submit a pull request

### Development Guidelines
- Follow existing code patterns (async/await, Pydantic models)
- Add tests for new functionality
- Update documentation (README.md, CLAUDE.md)
- Ensure Docker services build and start correctly

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **OpenRouter** - Multi-model API access
- **ElevenLabs** - High-quality voice synthesis
- **Qdrant** - High-performance vector database  
- **FastAPI** - Modern Python web framework
- **Ollama** - Local LLM serving

---

**Built for the future of AI interaction** 🚀

*Ready to enhance, extend, and deploy. Core functionality operational with clear roadmap for advanced features.*