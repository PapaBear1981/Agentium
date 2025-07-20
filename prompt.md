 You will generate a full end‑to‑end implementation based on these requirements:

---

## 🧠 Project Scope & Goals

Design and implement a **Jarvis‑style, voice‑enabled multi‑agent AI system** featuring:
- Voice input (live mic) and voice output (speakers) via open-source STT/TTS or ElevenLabs API
- Multiple agents using different LLMs (OpenRouter & Ollama)
- Real‑time WebSocket frontend for live streaming voice/text
- Persistent memory and audit logs in PostgreSQL
- Vector retrieval and RAG using Qdrant
- File ingestion and storage for RAG
- Dynamic tool installation via Smithery MCP registry and AutoGen’s `McpWorkbench`
- Reflexion‑based self‑improvement loops
- Cost tracking and budget control in DB
- Containerized via Docker Compose
- Extensible for future RL pipeline integration

---

## 🔉 Voice Control

- Input: live microphone audio via open-source STT (e.g., WhisperX, Vocode) or optional ElevenLabs / AssemblyAI ASR :contentReference[oaicite:1]{index=1}  
- Output: real‑time TTS through open models (Coqui, pyttsx3, Dia) or ElevenLabs :contentReference[oaicite:2]{index=2}  
- Alternative: use Pipecat framework for full voice‑pipeline orchestration :contentReference[oaicite:3]{index=3}

---

## 👥 Agent LLM Configurations

Agents initialized with distinct LLMs:

```python
from autogen_ext.models.openai import OpenAIChatCompletionClient
from autogen_ext.models.ollama import OllamaChatCompletionClient

agent_clients = {
  "agent1_openrouter_gpt40": OpenAIChatCompletionClient(
      model="gpt-4o",
      base_url="https://openrouter.ai/api/v1",
      api_key=env("OPENROUTER_API_KEY")
  ),
  "agent2_ollama_gemma3_7b": OllamaChatCompletionClient(model="gemma3-7b"),
  "agent3_openrouter_gemini25": OpenAIChatCompletionClient(
      model="gemini-2.5-flash",
      base_url="https://openrouter.ai/api/v1",
      api_key=env("OPENROUTER_API_KEY")
  ),
  "agent4_ollama_llama4_32b": OllamaChatCompletionClient(model="llama4-32b")
}
Agents have independent model_clients and can be swapped as needed.

All agents have access to shared infra: PostgreSQL, pgvector, Qdrant, /data/docs, MCP tools via Smithery and McpWorkbench.

🏗️ Infrastructure Components
PostgreSQL + pgvector – Tables: chat_logs, tool_registry, cost_history, file_index, reflexion_log

Qdrant – Vector store for RAG and retrieval

File volume – /data/docs for persistent file storage

Ollama Daemon – Docker service for gemma3‑7b & llama4‑32b

Agent Service – Python process handling Autogen orchestration, MCP, Reflexion, voice

FastAPI WebSocket API – Streams WebSocket for voice/text interactions

Docker Compose – Brings all services together

Smithery MCP CLI – For tool discovery, install, plus MCPSafetyScanner validation

🗂️ ManagerAgent Workflow
Task reception via UserProxyAgent (WebSocket)

STT – Convert mic audio to text

Task planning – Delegate to appropriate agent(s)

MCP tool check – Query McpWorkbench.list_tools(), if missing → smithery install, validate via MCPSafetyScanner, reload, log in DB

Tool execution – Call tool, stream tool outputs, log cost to cost_history

Memory & RAG – Log chat/tools/output, embed and upsert into Qdrant, save files to /data/docs

LLM response – Return response via agent, synthesize text to speech, stream back over WebSocket

Reflexion – Analyze task success/failure, extract heuristics, store in reflexion_log

Summary & cleanup – Provide final summary, cost and vector index report

🧩 Constraints & Best Practices
Cost management – Budget LLM usage and log all consumption

Turn limit – max_turns=15 per user session

Security – Validate all MCP installs before use

Resilience – Robust retries and error handling

LLM swappability – Agents must support runtime model_client changes

Streaming – Real-time voice/text streaming via WebSocket

📁 Required Output Files
Generate these components with production-grade quality:

docker-compose.yml – Services: postgres+pgvector, qdrant, ollama, agent_service, fastapi_ws, voice_adapter

service/agent.py – Autogen orchestrator with agents, MCP, voice, memory, reflexion

service/db_schema.sql – PostgreSQL schema and indexes

service/retrieval.py – Qdrant vector and RAG integration

service/frontend.py – FastAPI WebSocket + voice pipeline

service/voice.py – STT/TTS adapters (WhisperX, Coqui, ElevenLabs)

service/mcp_integration.py – Smithery, McpWorkbench, MCPSafetyScanner utility

.env.example – Template for API keys and DB URLs

This prompt covers architecture, voice integration, tooling, DB design, and agents. Generate each file as clean, cohesive code following these instructions.