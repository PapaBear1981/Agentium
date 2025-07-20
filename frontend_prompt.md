# 🧠 Agentic Frontend Design Spec for Agentium AI System

## ⚙️ Overview

This frontend is the command bridge of the Agentium AI multi-agent backend system. It must:
- Be conversational-first (chat is the command interface)
- Integrate TTS/STT for real-time voice interaction via ElevenLabs
- Support multi-agent orchestration and live tool execution
- Allow file upload & download inline in chat
- Support Markdown, Graphs, CSV, PDF, TXT, .MD
- Provide rich animations and dark theme by default
- Be built with **Vue** and powered by **ShadCN**, **MagicUI**, and **MCP components**
- Run in **Docker Compose** with the backend stack

---

## 🧩 Component Layout (Based on Visuals Provided)

### Layout Structure
```
AgentiumApp.vue
├── Sidebar.vue        # Workspace, Agents, Search
├── Header.vue         # Model selector, session info
├── ChatView.vue
│   ├── ChatMessages.vue
│   ├── ChatInput.vue
│   ├── FileUpload.vue
│   └── VoiceControls.vue
├── AgentTools.vue     # Calendar, Calculator, Graph Builder, File Viewer
└── SettingsDrawer.vue
```

### Suggested Visual Flow
- 🌓 **Dark UI baseline** (Inspired by OpenRouter + Formable)
- ✨ Animations on:
  - Typing indicators
  - Tool responses
  - Voice transitions
  - Sidebar open/close
- 📁 Upload via drag-and-drop or icon next to input
- 📉 Graph/Chart panels open modally or inline
- 🔊 Voice status ring (recording / processing / speaking)

---

## 💬 Chat Experience

### Features
- Rich markdown output
- Streaming agent responses (typing effect)
- Inline buttons and dropdowns (via ShadCN + MagicUI)
- File previews for CSV, PDF, etc.
- Agent personality selector

### Actions in Chat
```plaintext
- "Generate a graph from this CSV"
- "Summarize this PDF"
- "Download system logs"
- "Switch to the Gemini Research Agent"
- "Show me a calendar view of upcoming tasks"
```

---

## 🎙️ Voice Integration

### Core States
- 🎤 Listening (STT) → 🔁 Processing → 🗣️ Speaking (TTS)

### ElevenLabs
- Uses `/voice_adapter` on port `8002`
- Visual mic pulse during recording
- Animated waveform during processing
- Audio player for playback of agent responses

---

## 📁 File Capabilities

### Chat Uploads (from input bar)
- PDF, CSV, .txt, .md
- Display previews with file name, type, and size
- Agent context aware of file contents

### Chat Downloads
- Download buttons under agent messages
- Automatic inline previews for text-based formats

---

## 📊 Tool Integration

### Embedded in Chat
- Calculator: math expressions, symbolic calc
- Calendar: reminders, deadlines, appointments
- Graphs: line/bar/pie rendered via chart.js or v-charts
- PDF/CSV renderer: ShadCN modal or MCP preview component

---

## 🔐 Authentication & Sessions

- Login/Logout support via backend JWT or session API
- Show user profile (avatar in bottom-left)
- Session context preserved on reconnect

---

## 🔧 Tech Stack

### Framework
- **Vue 3 + Vite**
- **TypeScript**

### UI Libraries
- **ShadCN/vue**
- **MagicUI**
- **Tailwind CSS**
- **VueUse** (for composables and utils)
- **Chart.js** or **v-charts** for graphing

### Audio/Voice
- Web Audio API (STT/WAV recorder)
- ElevenLabs TTS API
- Audio waveform visualization

### Realtime
- Native WebSocket client for FastAPI `/ws/{session_id}`

---

## 🐳 Docker Integration

### Docker Compose `frontend` Service
```yaml
frontend:
  build: ./frontend
  ports:
    - "8080:8080"
  depends_on:
    - fastapi_ws
    - agent_service
    - voice_adapter
  volumes:
    - ./frontend:/app
  environment:
    - VITE_API_BASE_URL=http://localhost:8000
    - VITE_AGENT_SERVICE=http://localhost:8001
    - VITE_VOICE_SERVICE=http://localhost:8002
```

---

## ✅ Must-Have Features Checklist

| Feature                     | Status     |
|----------------------------|------------|
| WebSocket Connection       | ✅ Built-in |
| TTS/STT w/ ElevenLabs      | ✅ Working  |
| File Uploads in Chat       | ✅ Required |
| Graph / Chart Output       | ✅ Required |
| Calendar + Calculator      | ✅ Required |
| PDF/CSV Reader             | ✅ Required |
| Dark Theme                 | ✅ Default  |
| Voice UI Feedback          | ✅ Needed   |
| Agent Switching UI         | ✅ Needed   |
| Animations                 | ✅ Must     |
| Docker Compose Integration | ✅ Must     |
| Markdown + Tables          | ✅ Required |

