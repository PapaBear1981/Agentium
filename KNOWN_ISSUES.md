# Known Issues and Development Notes

## 🚨 Current Issues

### High Priority

1. **AutoGen Framework Integration**
   - **Issue**: Type annotation conflicts in `service/agent.py`
   - **Error**: `AssertionError: Return type not found` in message handlers
   - **Workaround**: Using simplified agent service (`simple_agent_service.py`)
   - **Fix Needed**: Resolve string forward references and import issues

2. **RAG System Dependencies**
   - **Issue**: `sentence-transformers` package conflicts during Docker build
   - **Impact**: Vector embeddings and document processing disabled
   - **Workaround**: RAG imports wrapped in try/catch blocks
   - **Fix Needed**: Resolve dependency conflicts or use alternative embedding solution

3. **Qdrant Health Check**
   - **Issue**: Uses `/healthz` endpoint instead of standard `/health`
   - **Impact**: Test suite reports failure (but service works correctly)
   - **Fix Needed**: Update test expectations or standardize endpoint

### Medium Priority

4. **WebSocket Message Types**
   - **Issue**: Some message handlers expect different response formats
   - **Impact**: WebSocket heartbeat/status tests fail
   - **Current**: Basic WebSocket connection works
   - **Fix Needed**: Align message schemas between frontend and test expectations

5. **MCP Tools Integration**
   - **Issue**: Tool management endpoints not implemented in simplified version
   - **Impact**: `/tools` endpoint returns 404
   - **Status**: Planned for future implementation
   - **Dependencies**: Requires AutoGen framework fixes first

6. **Voice Service Status Endpoint**
   - **Issue**: `/status` endpoint returns 500 error
   - **Impact**: One voice test fails (but core STT/TTS works)
   - **Fix Needed**: Implement or fix status endpoint in voice service

### Low Priority

7. **Docker Health Checks**
   - **Issue**: Some containers lack `curl` for health checks
   - **Workaround**: Disabled problematic health checks
   - **Fix Needed**: Use proper health check tools or install curl in containers

8. **Service Dependencies**
   - **Issue**: Complex dependency chains cause startup delays
   - **Workaround**: Simplified to basic dependencies
   - **Fix Needed**: Implement proper health check waiting

## 🔧 Fixes Applied

### Completed Fixes

1. **Agent Service Port Exposure**
   - **Issue**: Agent service not accessible from host
   - **Fix**: Added `ports: ["8001:8001"]` to docker-compose.yml

2. **Heavy Dependencies**
   - **Issue**: Torch/transformers causing long build times and failures
   - **Fix**: Removed from requirements, made RAG optional

3. **Docker Build Issues**
   - **Issue**: Missing system tools in containers
   - **Fix**: Simplified health checks, removed tool dependencies

4. **Import Errors**
   - **Issue**: Module not found errors for optional dependencies
   - **Fix**: Added try/catch blocks around optional imports

## 🛠️ Development Workflow for Fixes

### For AutoGen Integration
```bash
# 1. Check original implementation
cat service/agent.py | grep -A 5 "@message_handler"

# 2. Fix type annotations
# - Ensure all async methods have return types
# - Use string forward references for complex types
# - Import required types properly

# 3. Test AutoGen directly
python -c "from service.agent import AgentOrchestrator"
```

### For RAG System
```bash
# 1. Add sentence-transformers back to requirements
echo "sentence-transformers>=2.2.2" >> service/requirements-agent.txt

# 2. Build with more memory
docker-compose build --memory=4g agent_service

# 3. Test imports
docker run --rm agents-agent_service python -c "from sentence_transformers import SentenceTransformer"
```

### For WebSocket Issues
```bash
# 1. Check message schemas
grep -r "WebSocketMessage" service/models/

# 2. Test WebSocket directly
# Use scripts/test_system.py WebSocket section as reference

# 3. Align schemas between frontend and tests
```

## 📋 Testing Strategy

### Current Test Coverage
- **Infrastructure**: 3/3 tests (PostgreSQL ✅, Ollama ✅, Qdrant ⚠️)
- **Services**: 5/7 tests (Agent ✅, Voice ✅, Frontend ✅, Tools ❌, Voice Status ❌)
- **Communication**: 2/5 tests (WebSocket ✅, Messages ❌)
- **Voice**: 2/2 tests (STT ✅, TTS ✅)
- **Integration**: 2/3 tests (Agent ✅, Metrics ✅, E2E ❌)

### Test Command
```bash
# Run all tests
python scripts/test_system.py

# Expected result: ~70% pass rate (14/20 tests)
```

## 🎯 Next Sprint Priorities

### Week 1: Core Stability
1. Fix AutoGen type annotations
2. Re-enable RAG with lighter dependencies
3. Standardize health check endpoints

### Week 2: Feature Completion
1. Complete WebSocket message handlers
2. Implement MCP tools basic version
3. Add comprehensive error handling

### Week 3: Performance & UX
1. Add web UI frontend
2. Optimize startup times
3. Add monitoring dashboard

## 💡 Architecture Decisions

### Why Simplified Agent Service?
- **Problem**: AutoGen framework had complex type annotation issues
- **Decision**: Created minimal working version to maintain momentum
- **Trade-off**: Lost advanced multi-agent orchestration for reliability
- **Plan**: Gradually migrate back to AutoGen once issues resolved

### Why Disable RAG Initially?
- **Problem**: sentence-transformers caused Docker build failures
- **Decision**: Make RAG optional to get core system running
- **Trade-off**: No document retrieval, but agents still functional
- **Plan**: Re-enable with alternative embedding approach

### Why Remove Health Checks?
- **Problem**: Containers missing curl/wget for health checks
- **Decision**: Simplified checks to prevent startup failures
- **Trade-off**: Less robust health monitoring
- **Plan**: Add proper health check tooling to containers

## 🔍 Debugging Commands

### Service Status
```bash
# Check all services
docker-compose ps

# Check specific service logs
docker-compose logs -f agent_service
docker-compose logs -f voice_adapter
docker-compose logs -f fastapi_ws

# Check health endpoints
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:6333/healthz
```

### Network Connectivity
```bash
# Test inter-service communication
docker exec jarvis_agent_service curl http://fastapi_ws:8000/health
docker exec jarvis_fastapi_ws curl http://agent_service:8001/health
```

### Resource Usage
```bash
# Check container resources
docker stats

# Check disk usage
docker system df
```

This document should be updated as issues are resolved and new ones discovered.