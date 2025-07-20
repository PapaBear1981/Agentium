# COMPREHENSIVE FRONTEND INTEGRATION GUIDE
# Jarvis Multi-Agent AI System

## 🚀 EXECUTIVE SUMMARY

This is a sophisticated multi-agent AI system with real-time voice and text interaction capabilities. The frontend must integrate with:

- **FastAPI WebSocket Server** (port 8000) - Real-time communication hub
- **Agent Service** (port 8001) - AutoGen-based multi-agent orchestration  
- **Voice Service** (port 8002) - Speech-to-Text and Text-to-Speech processing
- **Supporting Infrastructure** - PostgreSQL, Qdrant vector DB, Ollama LLM, Redis

## 🏗️ SYSTEM ARCHITECTURE

### Service Layout
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │  FastAPI WS     │    │  Agent Service  │
│  (Your Code)    │◄──►│  Port 8000      │◄──►│  Port 8001      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Voice Service  │    │  PostgreSQL     │
                       │  Port 8002      │    │  Port 5432      │
                       └─────────────────┘    └─────────────────┘
                                │                        │
                       ┌─────────────────┐    ┌─────────────────┐
                       │  Qdrant Vector  │    │  Ollama LLM     │
                       │  Port 6333      │    │  Port 11434     │
                       └─────────────────┘    └─────────────────┘
```

### Docker Services Overview
- **fastapi_ws**: Main WebSocket communication layer
- **agent_service**: Multi-agent orchestration with GPT-4o, Gemini, local models
- **voice_adapter**: Voice processing with multiple provider support
- **postgres**: Database with pgvector extension for embeddings
- **qdrant**: Vector database for RAG functionality
- **ollama**: Local LLM serving (Gemma2-7B, Llama3.2-8B)
- **redis**: Caching and session management

## 📡 WEBSOCKET API SPECIFICATION

### Connection Endpoint
```
ws://localhost:8000/ws/{session_id}
```

### Message Protocol
All messages follow JSON format with `type` and `data` fields:

```typescript
interface WebSocketMessage {
  type: string;
  data: any;
  timestamp: string;
  session_id: string;
}
```

### Message Types

#### Client to Server
```typescript
// Voice input (base64 encoded audio)
{
  type: "voice_input",
  data: {
    audio: string,        // base64 encoded audio
    format: "wav" | "mp3" | "webm",
    sample_rate: number
  }
}

// Text input
{
  type: "text_input",
  data: {
    message: string,
    context?: any
  }
}

// System commands
{
  type: "system_command",
  data: {
    command: "pause" | "resume" | "reset" | "status"
  }
}
```

#### Server to Client
```typescript
// Agent responses
{
  type: "agent_response",
  data: {
    agent_id: string,
    message: string,
    audio?: string,      // base64 encoded TTS audio
    metadata: {
      model: string,
      tokens_used: number,
      cost: number
    }
  }
}

// Tool execution updates
{
  type: "tool_execution",
  data: {
    tool_name: string,
    status: "started" | "completed" | "failed",
    result?: any,
    error?: string
  }
}

// System status
{
  type: "system_status",
  data: {
    agents_active: number,
    session_cost: number,
    budget_remaining: number,
    voice_processing: boolean
  }
}

// Cost updates
{
  type: "cost_update",
  data: {
    session_cost: number,
    last_operation_cost: number,
    budget_remaining: number,
    warning?: string
  }
}
```

## 🌐 HTTP API ENDPOINTS

### Frontend Service (Port 8000) - Main Integration Point

#### Health & System Status
```bash
GET http://localhost:8000/health
```
```json
Response: {
  "status": "healthy",
  "active_connections": 5,
  "timestamp": 1674123456.789
}
```

#### WebSocket Connection Management
```bash
GET http://localhost:8000/connections
```
```json
Response: {
  "active_connections": 3,
  "sessions": {
    "session-123": {
      "connected_at": 1674123400.0,
      "message_count": 25,
      "last_activity": 1674123456.0,
      "duration_seconds": 56
    }
  }
}
```

#### Session Management
```bash
GET http://localhost:8000/sessions/{session_id}
```
```json
Response: {
  "connected_at": 1674123400.0,
  "message_count": 25,
  "last_activity": 1674123456.0,
  "total_cost": 0.45,
  "message_history_count": 12,
  "voice_enabled": true,
  "current_agent": "agent1_openrouter_gpt40"
}
```

```bash
DELETE http://localhost:8000/sessions/{session_id}
```
```json
Response: {
  "success": true,
  "message": "Session session-123 disconnected"
}
```

#### Broadcasting Messages
```bash
POST http://localhost:8000/broadcast
Content-Type: application/json
```
```json
Body: {
  "message": "System maintenance in 5 minutes",
  "type": "system_announcement"
}

Response: {
  "success": true,
  "message": "Message broadcasted",
  "recipients": 5
}
```

### Agent Service (Port 8001) - Core AI Processing

#### Health Check
```bash
GET http://localhost:8001/health
```
```json
Response: {
  "status": "healthy",
  "agents": ["agent1_openrouter_gpt40", "agent2_ollama_gemma3_7b"],
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### Task Processing (Main Endpoint)
```bash
POST http://localhost:8001/tasks/process
Content-Type: application/json
```
```json
Body: {
  "content": "Explain quantum computing in simple terms",
  "session_id": "session-123",
  "context": {
    "user_level": "beginner",
    "preferred_agent": "agent1_openrouter_gpt40"
  },
  "priority": "medium"
}

Response: {
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "result": "Quantum computing is like having a super-powered computer...",
  "agent_id": "agent1_openrouter_gpt40",
  "success": true,
  "tokens_used": 150,
  "cost": 0.003,
  "processing_time_ms": 2500,
  "metadata": {
    "model": "gpt-4o",
    "provider": "openrouter"
  }
}
```

#### Agent Status and Management
```bash
GET http://localhost:8001/status
```
```json
Response: {
  "agents": [
    {
      "id": "agent1_openrouter_gpt40",
      "name": "GPT-4o Reasoning Agent", 
      "model": "gpt-4o",
      "provider": "openrouter",
      "status": "active",
      "tasks_completed": 45,
      "tasks_failed": 2,
      "total_tokens_used": 12500,
      "total_cost": 2.45,
      "average_response_time_ms": 2200.5
    },
    {
      "id": "agent2_ollama_gemma3_7b",
      "name": "Gemma2 Local Agent",
      "model": "gemma2:7b", 
      "provider": "ollama",
      "status": "idle",
      "tasks_completed": 23,
      "tasks_failed": 0,
      "total_tokens_used": 8900,
      "total_cost": 0.0,
      "average_response_time_ms": 1850.3
    }
  ],
  "manager_status": "active",
  "active_sessions": 3,
  "task_queue_size": 0
}
```

### Voice Service (Port 8002) - Speech Processing

#### Health Check
```bash
GET http://localhost:8002/health  
```
```json
Response: {
  "status": "healthy",
  "stt_provider": "elevenlabs",
  "tts_provider": "elevenlabs", 
  "providers_available": {
    "stt_elevenlabs": true,
    "tts_elevenlabs": true,
    "stt_whisperx": false,
    "tts_coqui": false
  },
  "timestamp": "2024-01-20T10:30:00Z"
}
```

#### Speech-to-Text (STT)
```bash
POST http://localhost:8002/stt
Content-Type: application/json
```
```json
Body: {
  "audio_data": "base64_encoded_audio_data_here",
  "format": "wav",
  "sample_rate": 16000,
  "session_id": "session-123"
}

Response: {
  "success": true,
  "text": "Hello, can you help me with my project?",
  "confidence": 0.95,
  "language": "en",
  "processing_time_ms": 1200,
  "provider": "elevenlabs",
  "model": "whisper-1"
}
```

#### Text-to-Speech (TTS)  
```bash
POST http://localhost:8002/tts
Content-Type: application/json
```
```json
Body: {
  "text": "I'd be happy to help you with your project!",
  "voice": "default",
  "speed": 1.0,
  "session_id": "session-123"
}

Response: {
  "success": true,
  "audio_data": "base64_encoded_audio_data_here",
  "format": "mp3",
  "sample_rate": 22050,
  "duration_ms": 3500,
  "processing_time_ms": 800,
  "provider": "elevenlabs",
  "voice": "default"
}
```

#### Voice Performance Metrics
```bash
GET http://localhost:8002/metrics
```
```json
Response: {
  "stt_requests": 156,
  "stt_success_rate": 0.97,
  "stt_avg_processing_time_ms": 1150.5,
  "tts_requests": 134, 
  "tts_success_rate": 0.99,
  "tts_avg_processing_time_ms": 750.2,
  "total_audio_processed_seconds": 1847.3,
  "errors": 5
}
```

## 🎯 AVAILABLE AGENTS AND THEIR CAPABILITIES

### Agent Profiles
The system includes 4 specialized agents accessible via the Agent Service:

#### 1. GPT-4o Reasoning Agent (`agent1_openrouter_gpt40`)
- **Role**: Advanced reasoning and problem-solving
- **Model**: GPT-4o via OpenRouter
- **Best For**: Complex analysis, coding, detailed explanations
- **Cost**: ~$0.003 per 1K tokens
- **Response Time**: 2-3 seconds

#### 2. Gemma2 Local Agent (`agent2_ollama_gemma3_7b`) 
- **Role**: Fast local processing
- **Model**: Gemma2-7B via Ollama
- **Best For**: Quick responses, basic tasks, privacy-sensitive queries
- **Cost**: Free (local)
- **Response Time**: 1-2 seconds

#### 3. Gemini Research Agent (`agent3_openrouter_gemini25`)
- **Role**: Research and information gathering
- **Model**: Gemini-2.5-Flash via OpenRouter
- **Best For**: Research, fact-finding, analysis
- **Cost**: ~$0.002 per 1K tokens  
- **Response Time**: 2-3 seconds

#### 4. Llama Local Agent (`agent4_ollama_llama4_32b`)
- **Role**: Critical thinking and review
- **Model**: Llama3.2-8B via Ollama
- **Best For**: Code review, critique, feedback
- **Cost**: Free (local)
- **Response Time**: 2-4 seconds

### Agent Selection Logic
The Manager Agent automatically routes tasks based on keywords:
- **Code/Programming**: → GPT-4o Agent
- **Search/Research**: → Gemini Agent  
- **Analysis/Data**: → Gemma2 Agent
- **Default**: → First available agent

## 🗄️ DATA MODELS AND STRUCTURES

### Core WebSocket Message Types
```typescript
// Base message structure
interface WebSocketMessage {
  type: WebSocketMessageType;
  data: any;
  timestamp: string;
  session_id?: string;
  message_id?: string;
}

// Message type enumeration
enum WebSocketMessageType {
  // Client to Server
  VOICE_INPUT = "voice_input",
  TEXT_INPUT = "text_input", 
  SYSTEM_COMMAND = "system_command",
  
  // Server to Client
  AGENT_RESPONSE = "agent_response",
  AGENT_RESPONSE_STREAM = "agent_response_stream",
  TOOL_EXECUTION = "tool_execution",
  SYSTEM_STATUS = "system_status",
  COST_UPDATE = "cost_update",
  ERROR = "error",
  
  // Bidirectional
  HEARTBEAT = "heartbeat",
  CONNECTION_STATUS = "connection_status"
}
```

### Voice Processing Models
```typescript
// STT Request
interface STTRequest {
  audio_data: string;        // base64 encoded
  format: "wav" | "mp3" | "webm";
  sample_rate: number;       // typically 16000
  channels: number;          // typically 1
  language?: string;         // default "en" 
  session_id?: string;
}

// STT Response
interface STTResponse {
  text: string;
  confidence?: number;       // 0.0 to 1.0
  language?: string;
  processing_time_ms: number;
  provider: "elevenlabs" | "whisperx" | "faster_whisper";
  model: string;
  segments?: Array<{        // word-level timestamps
    start: number;
    end: number;
    text: string;
    confidence: number;
  }>;
  success: boolean;
  error?: string;
}

// TTS Request  
interface TTSRequest {
  text: string;
  voice?: string;           // default "default"
  language: string;         // default "en"
  speed: number;            // 0.1 to 3.0, default 1.0
  format: "wav" | "mp3";
  session_id?: string;
}

// TTS Response
interface TTSResponse {
  audio_data: string;       // base64 encoded audio
  format: "wav" | "mp3";
  sample_rate: number;
  duration_ms: number;
  processing_time_ms: number;
  provider: "elevenlabs" | "coqui" | "pyttsx3";
  voice: string;
  success: boolean;
  error?: string;
}
```

### Agent and Task Models
```typescript
// Agent Status
interface AgentStatus {
  agent_id: string;
  name: string;
  model: string;
  provider: "openrouter" | "ollama";
  status: "active" | "idle" | "busy" | "error";
  tasks_completed: number;
  tasks_failed: number;
  total_tokens_used: number;
  total_cost: number;
  average_response_time_ms: number;
}

// Task Request (sent to agent service)
interface TaskRequest {
  content: string;          // user's message/request
  session_id: string;
  context?: {               // optional context
    user_level?: string;
    preferred_agent?: string;
    conversation_history?: Array<any>;
  };
  priority: "low" | "medium" | "high" | "urgent";
}

// Task Response (from agent service)
interface TaskResponse {
  task_id: string;
  result: string;           // agent's response text
  agent_id: string;
  success: boolean;
  tokens_used: number;
  cost: number;             // in USD
  processing_time_ms: number;
  metadata: {
    model: string;
    provider: string;
    temperature?: number;
  };
}
```

## 🔧 ENVIRONMENT CONFIGURATION

### Required Environment Variables
```bash
# API Keys
OPENROUTER_API_KEY=your_openrouter_key_here
ELEVENLABS_API_KEY=your_elevenlabs_key_here

# Voice Configuration  
STT_PROVIDER=elevenlabs          # or whisperx, faster_whisper
TTS_PROVIDER=elevenlabs          # or coqui, pyttsx3

# System Configuration
MAX_TURNS=15                     # max conversation turns
BUDGET_LIMIT=100.00             # USD budget limit per session
LOG_LEVEL=INFO                  # DEBUG, INFO, WARNING, ERROR

# Database (auto-configured in Docker)
DATABASE_URL=postgresql://jarvis_user:password@postgres:5432/jarvis
QDRANT_URL=http://qdrant:6333
OLLAMA_URL=http://ollama:11434

# CORS (for frontend)
CORS_ORIGINS=http://localhost:3000,http://localhost:8080
```

### Docker Compose Services
All services are defined in `docker-compose.yml`:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f fastapi_ws     # WebSocket service
docker-compose logs -f agent_service  # Agent processing
docker-compose logs -f voice_adapter  # Voice processing

# Health checks
curl http://localhost:8000/health     # Frontend service
curl http://localhost:8001/health     # Agent service  
curl http://localhost:8002/health     # Voice service
curl http://localhost:6333/healthz   # Qdrant (note: /healthz not /health)
curl http://localhost:11434/api/tags # Ollama
```

## 💻 FRONTEND IMPLEMENTATION GUIDE

### State Management
```typescript
interface AppState {
  // Connection state
  connected: boolean;
  session_id: string;
  websocket: WebSocket | null;
  reconnectAttempts: number;

  // Conversation state
  messages: ChatMessage[];
  currentAgent: string;
  conversationHistory: ConversationTurn[];
  
  // Voice state
  recording: boolean;
  speaking: boolean;
  voiceEnabled: boolean;
  audioContext: AudioContext | null;
  mediaRecorder: MediaRecorder | null;

  // System state
  agents: AgentStatus[];
  systemHealth: SystemHealth;
  costSummary: CostSummary;
  sessionStats: SessionStats;

  // UI state
  sidebarOpen: boolean;
  settingsOpen: boolean;
  theme: "light" | "dark";
  currentView: "chat" | "agents" | "settings";
}

interface ChatMessage {
  id: string;
  type: "user" | "agent" | "system";
  content: string;
  timestamp: Date;
  agentId?: string;
  agentName?: string;
  cost?: number;
  tokens?: number;
  processingTime?: number;
  audioData?: string;  // base64 encoded TTS audio
  metadata?: any;
}

interface SystemHealth {
  overall: "healthy" | "degraded" | "unhealthy";
  services: {
    websocket: boolean;
    agents: boolean;
    voice: boolean;
    database: boolean;
  };
  lastCheck: Date;
}

interface CostSummary {
  sessionCost: number;
  budgetLimit: number;
  budgetRemaining: number;
  costBreakdown: Record<string, number>;
  lastUpdate: Date;
}
```

### Component Architecture
```
App/
├── Layout/
│   ├── Header/
│   │   ├── ConnectionIndicator      # WebSocket status
│   │   ├── CostMeter               # Budget display  
│   │   ├── AgentSelector           # Current agent display
│   │   └── SettingsToggle
│   ├── Sidebar/
│   │   ├── AgentStatusPanel        # Live agent metrics
│   │   ├── SessionHistory          # Past conversations
│   │   ├── SystemHealth            # Service status
│   │   └── QuickActions            # Common commands
│   └── Footer/
│       ├── VoiceControls           # Mic/speaker controls
│       ├── ConnectionStatus        # WebSocket state
│       └── BudgetWarning           # Cost alerts
├── Chat/
│   ├── MessageList/
│   │   ├── UserMessage             # User input display
│   │   ├── AgentMessage            # Agent response with audio
│   │   ├── SystemMessage           # Status/error messages
│   │   └── TypingIndicator         # Agent processing state
│   ├── InputArea/
│   │   ├── TextInput               # Text message input
│   │   ├── VoiceInput              # Voice recording controls
│   │   ├── FileUpload              # Document upload
│   │   └── SendButton
│   └── VoicePlayer/                # Audio playback controls
│       ├── AudioWaveform           # Visual audio feedback
│       ├── PlaybackControls        # Play/pause/stop
│       └── VolumeControl
├── Voice/
│   ├── VoiceRecorder/              # Audio recording
│   │   ├── MicrophoneAccess        # Permission handling
│   │   ├── AudioVisualizer         # Real-time waveform
│   │   ├── VoiceActivityDetection  # Auto start/stop
│   │   └── RecordingControls       # Manual controls
│   └── AudioProcessor/             # Audio utilities
│       ├── AudioEncoder            # Format conversion
│       ├── NoiseReduction          # Audio cleanup
│       └── CompressionUtils        # Size optimization
└── Settings/
    ├── VoiceSettings/              # STT/TTS configuration
    ├── AgentPreferences/           # Agent selection
    ├── BudgetControls/             # Cost management
    └── UIPreferences/              # Theme, layout, etc.
```

## 🔌 WEBSOCKET INTEGRATION PATTERNS

### Connection Management
```typescript
class WebSocketManager {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectInterval = 1000;
  private sessionId: string;
  
  constructor(sessionId: string) {
    this.sessionId = sessionId;
  }
  
  async connect(): Promise<boolean> {
    try {
      this.ws = new WebSocket(`ws://localhost:8000/ws/${this.sessionId}`);
      
      this.ws.onopen = () => {
        console.log('WebSocket connected');
        this.reconnectAttempts = 0;
        this.onConnectionChange?.(true);
      };
      
      this.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        this.handleMessage(message);
      };
      
      this.ws.onclose = () => {
        console.log('WebSocket disconnected');
        this.onConnectionChange?.(false);
        this.attemptReconnect();
      };
      
      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        this.onError?.(error);
      };
      
      return true;
    } catch (error) {
      console.error('Failed to connect:', error);
      return false;
    }
  }
  
  private attemptReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      setTimeout(() => {
        console.log(`Reconnection attempt ${this.reconnectAttempts}`);
        this.connect();
      }, this.reconnectInterval * this.reconnectAttempts);
    }
  }
  
  sendMessage(type: string, data: any) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      const message = {
        type,
        data,
        timestamp: new Date().toISOString(),
        session_id: this.sessionId
      };
      this.ws.send(JSON.stringify(message));
    }
  }
  
  sendTextMessage(text: string, context?: any) {
    this.sendMessage('text_input', {
      message: text,
      context
    });
  }
  
  sendVoiceMessage(audioData: string, format = 'wav', sampleRate = 16000) {
    this.sendMessage('voice_input', {
      audio: audioData,
      format,
      sample_rate: sampleRate
    });
  }
  
  sendSystemCommand(command: string, parameters?: any) {
    this.sendMessage('system_command', {
      command,
      parameters
    });
  }
  
  private handleMessage(message: any) {
    switch (message.type) {
      case 'agent_response':
        this.onAgentResponse?.(message.data);
        break;
      case 'cost_update':
        this.onCostUpdate?.(message.data);
        break;
      case 'system_status':
        this.onSystemStatus?.(message.data);
        break;
      case 'error':
        this.onError?.(message.data);
        break;
      default:
        console.log('Unknown message type:', message.type);
    }
  }
  
  // Event handlers (set these from your component)
  onConnectionChange?: (connected: boolean) => void;
  onAgentResponse?: (data: any) => void;
  onCostUpdate?: (data: any) => void;
  onSystemStatus?: (data: any) => void;
  onError?: (error: any) => void;
}
```

### React Hook Example
```typescript
function useWebSocket(sessionId: string) {
  const [connected, setConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [costSummary, setCostSummary] = useState<CostSummary | null>(null);
  const wsManager = useRef<WebSocketManager | null>(null);
  
  useEffect(() => {
    wsManager.current = new WebSocketManager(sessionId);
    
    wsManager.current.onConnectionChange = setConnected;
    
    wsManager.current.onAgentResponse = (data) => {
      const message: ChatMessage = {
        id: crypto.randomUUID(),
        type: 'agent',
        content: data.message,
        timestamp: new Date(),
        agentId: data.agent_id,
        agentName: data.agent_name,
        cost: data.cost,
        tokens: data.tokens_used,
        processingTime: data.processing_time_ms,
        audioData: data.audio
      };
      setMessages(prev => [...prev, message]);
      
      // Play audio if available
      if (data.audio) {
        playAudio(data.audio);
      }
    };
    
    wsManager.current.onCostUpdate = (data) => {
      setCostSummary({
        sessionCost: data.session_cost,
        budgetLimit: data.budget_limit,
        budgetRemaining: data.budget_remaining,
        costBreakdown: data.cost_breakdown || {},
        lastUpdate: new Date()
      });
    };
    
    wsManager.current.connect();
    
    return () => {
      wsManager.current?.ws?.close();
    };
  }, [sessionId]);
  
  const sendTextMessage = useCallback((text: string) => {
    wsManager.current?.sendTextMessage(text);
    
    // Add user message to UI immediately
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      content: text,
      timestamp: new Date()
    };
    setMessages(prev => [...prev, userMessage]);
  }, []);
  
  const sendVoiceMessage = useCallback((audioData: string) => {
    wsManager.current?.sendVoiceMessage(audioData);
  }, []);
  
  return {
    connected,
    messages,
    costSummary,
    sendTextMessage,
    sendVoiceMessage
  };
}
```

## 🎤 VOICE INTEGRATION IMPLEMENTATION

### Complete Audio Recording System
```typescript
class AudioRecordingManager {
  private mediaRecorder: MediaRecorder | null = null;
  private audioChunks: Blob[] = [];
  private stream: MediaStream | null = null;
  private audioContext: AudioContext | null = null;
  private analyser: AnalyserNode | null = null;
  
  async initializeAudio(): Promise<boolean> {
    try {
      // Request microphone access
      this.stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: 16000,
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        }
      });
      
      // Create audio context for analysis
      this.audioContext = new AudioContext({ sampleRate: 16000 });
      const source = this.audioContext.createMediaStreamSource(this.stream);
      this.analyser = this.audioContext.createAnalyser();
      this.analyser.fftSize = 256;
      source.connect(this.analyser);
      
      // Create MediaRecorder
      this.mediaRecorder = new MediaRecorder(this.stream, {
        mimeType: 'audio/webm;codecs=opus'
      });
      
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data);
        }
      };
      
      this.mediaRecorder.onstop = () => {
        this.processRecording();
      };
      
      return true;
    } catch (error) {
      console.error('Failed to initialize audio:', error);
      return false;
    }
  }
  
  startRecording(): boolean {
    if (this.mediaRecorder?.state === 'inactive') {
      this.audioChunks = [];
      this.mediaRecorder.start();
      this.onRecordingStart?.();
      return true;
    }
    return false;
  }
  
  stopRecording(): boolean {
    if (this.mediaRecorder?.state === 'recording') {
      this.mediaRecorder.stop();
      this.onRecordingStop?.();
      return true;
    }
    return false;
  }
  
  private async processRecording() {
    const audioBlob = new Blob(this.audioChunks, { type: 'audio/webm' });
    
    // Convert to WAV and encode to base64
    const arrayBuffer = await audioBlob.arrayBuffer();
    const audioData = await this.convertToWav(arrayBuffer);
    const base64Audio = this.arrayBufferToBase64(audioData);
    
    this.onRecordingComplete?.(base64Audio);
  }
  
  private async convertToWav(webmBuffer: ArrayBuffer): Promise<ArrayBuffer> {
    // Use Web Audio API to decode and re-encode as WAV
    const audioBuffer = await this.audioContext!.decodeAudioData(webmBuffer);
    return this.audioBufferToWav(audioBuffer);
  }
  
  private audioBufferToWav(audioBuffer: AudioBuffer): ArrayBuffer {
    const length = audioBuffer.length;
    const sampleRate = audioBuffer.sampleRate;
    const numberOfChannels = 1; // Force mono
    
    // Get channel data
    const channelData = audioBuffer.getChannelData(0);
    
    // Create WAV file
    const arrayBuffer = new ArrayBuffer(44 + length * 2);
    const view = new DataView(arrayBuffer);
    
    // WAV header
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
      }
    };
    
    writeString(0, 'RIFF');
    view.setUint32(4, 36 + length * 2, true);
    writeString(8, 'WAVE');
    writeString(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, numberOfChannels, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * numberOfChannels * 2, true);
    view.setUint16(32, numberOfChannels * 2, true);
    view.setUint16(34, 16, true);
    writeString(36, 'data');
    view.setUint32(40, length * 2, true);
    
    // Convert float samples to 16-bit PCM
    let offset = 44;
    for (let i = 0; i < length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]));
      view.setInt16(offset, sample * 0x7FFF, true);
      offset += 2;
    }
    
    return arrayBuffer;
  }
  
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
  }
  
  getAudioLevel(): number {
    if (!this.analyser) return 0;
    
    const dataArray = new Uint8Array(this.analyser.frequencyBinCount);
    this.analyser.getByteFrequencyData(dataArray);
    
    const sum = dataArray.reduce((a, b) => a + b, 0);
    return sum / dataArray.length / 255;
  }
  
  cleanup() {
    this.stream?.getTracks().forEach(track => track.stop());
    this.audioContext?.close();
  }
  
  // Event callbacks
  onRecordingStart?: () => void;
  onRecordingStop?: () => void;
  onRecordingComplete?: (base64Audio: string) => void;
}
```

### Voice Activity Detection
```typescript
class VoiceActivityDetector {
  private audioManager: AudioRecordingManager;
  private isListening = false;
  private silenceTimer: NodeJS.Timeout | null = null;
  private speechTimer: NodeJS.Timeout | null = null;
  
  constructor(audioManager: AudioRecordingManager) {
    this.audioManager = audioManager;
  }
  
  start(options: {
    threshold: number = 0.1,
    silenceTimeout: number = 2000,
    speechTimeout: number = 500
  } = {}) {
    this.isListening = true;
    this.monitor(options);
  }
  
  stop() {
    this.isListening = false;
    if (this.silenceTimer) clearTimeout(this.silenceTimer);
    if (this.speechTimer) clearTimeout(this.speechTimer);
  }
  
  private monitor(options: any) {
    if (!this.isListening) return;
    
    const level = this.audioManager.getAudioLevel();
    const isVoice = level > options.threshold;
    
    if (isVoice) {
      // Voice detected
      if (this.silenceTimer) {
        clearTimeout(this.silenceTimer);
        this.silenceTimer = null;
      }
      
      if (!this.audioManager.mediaRecorder || 
          this.audioManager.mediaRecorder.state === 'inactive') {
        // Start recording after brief delay to avoid false positives
        if (!this.speechTimer) {
          this.speechTimer = setTimeout(() => {
            this.audioManager.startRecording();
            this.onSpeechStart?.();
            this.speechTimer = null;
          }, options.speechTimeout);
        }
      }
    } else {
      // Silence detected
      if (this.speechTimer) {
        clearTimeout(this.speechTimer);
        this.speechTimer = null;
      }
      
      if (this.audioManager.mediaRecorder?.state === 'recording') {
        if (!this.silenceTimer) {
          this.silenceTimer = setTimeout(() => {
            this.audioManager.stopRecording();
            this.onSpeechEnd?.();
            this.silenceTimer = null;
          }, options.silenceTimeout);
        }
      }
    }
    
    // Continue monitoring
    requestAnimationFrame(() => this.monitor(options));
  }
  
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
}
```

### Audio Playback Manager
```typescript
class AudioPlaybackManager {
  private currentAudio: HTMLAudioElement | null = null;
  private playbackQueue: string[] = [];
  private isPlaying = false;
  
  async playAudio(base64Audio: string, format = 'mp3'): Promise<void> {
    return new Promise((resolve, reject) => {
      const audio = new Audio();
      audio.src = `data:audio/${format};base64,${base64Audio}`;
      
      audio.onloadeddata = () => {
        this.onAudioReady?.(audio.duration);
      };
      
      audio.onplay = () => {
        this.isPlaying = true;
        this.onPlaybackStart?.();
      };
      
      audio.onended = () => {
        this.isPlaying = false;
        this.onPlaybackEnd?.();
        this.processQueue();
        resolve();
      };
      
      audio.onerror = (error) => {
        this.isPlaying = false;
        this.onPlaybackError?.(error);
        reject(error);
      };
      
      this.currentAudio = audio;
      audio.play().catch(reject);
    });
  }
  
  queueAudio(base64Audio: string) {
    if (this.isPlaying) {
      this.playbackQueue.push(base64Audio);
    } else {
      this.playAudio(base64Audio);
    }
  }
  
  private processQueue() {
    if (this.playbackQueue.length > 0) {
      const nextAudio = this.playbackQueue.shift()!;
      this.playAudio(nextAudio);
    }
  }
  
  stopPlayback() {
    if (this.currentAudio) {
      this.currentAudio.pause();
      this.currentAudio.currentTime = 0;
      this.isPlaying = false;
    }
    this.playbackQueue = [];
  }
  
  setVolume(volume: number) {
    if (this.currentAudio) {
      this.currentAudio.volume = Math.max(0, Math.min(1, volume));
    }
  }
  
  // Event callbacks
  onAudioReady?: (duration: number) => void;
  onPlaybackStart?: () => void;
  onPlaybackEnd?: () => void;
  onPlaybackError?: (error: any) => void;
}
```

## ⚠️ ERROR HANDLING AND EDGE CASES

### Connection Error Management
```typescript
interface ErrorHandler {
  handleWebSocketError(error: Event): void;
  handleVoiceError(error: VoiceError): void;
  handleAgentError(error: AgentError): void;
  handleNetworkError(error: NetworkError): void;
}

enum ErrorType {
  WEBSOCKET_CONNECTION_FAILED = "websocket_connection_failed",
  WEBSOCKET_MESSAGE_FAILED = "websocket_message_failed",
  VOICE_PERMISSION_DENIED = "voice_permission_denied",
  VOICE_NOT_SUPPORTED = "voice_not_supported",
  AUDIO_PROCESSING_FAILED = "audio_processing_failed",
  AGENT_SERVICE_UNAVAILABLE = "agent_service_unavailable",
  BUDGET_EXCEEDED = "budget_exceeded",
  RATE_LIMIT_EXCEEDED = "rate_limit_exceeded",
  NETWORK_TIMEOUT = "network_timeout"
}

class ErrorManager {
  private errorQueue: Error[] = [];
  private retryAttempts = new Map<string, number>();
  
  handleError(error: any, context: string) {
    console.error(`Error in ${context}:`, error);
    
    switch (error.type || this.classifyError(error)) {
      case ErrorType.WEBSOCKET_CONNECTION_FAILED:
        this.handleWebSocketError(error);
        break;
      case ErrorType.VOICE_PERMISSION_DENIED:
        this.handleVoicePermissionError();
        break;
      case ErrorType.BUDGET_EXCEEDED:
        this.handleBudgetError(error);
        break;
      case ErrorType.AGENT_SERVICE_UNAVAILABLE:
        this.handleAgentServiceError(error);
        break;
      default:
        this.handleGenericError(error, context);
    }
  }
  
  private handleWebSocketError(error: any) {
    // Show connection status to user
    this.onUIUpdate?.({
      type: 'connection_error',
      message: 'Connection lost. Attempting to reconnect...',
      severity: 'warning'
    });
    
    // Auto-retry with exponential backoff
    const retries = this.retryAttempts.get('websocket') || 0;
    if (retries < 5) {
      this.retryAttempts.set('websocket', retries + 1);
      setTimeout(() => {
        this.onRetryConnection?.();
      }, Math.pow(2, retries) * 1000);
    } else {
      this.onUIUpdate?.({
        type: 'connection_error',
        message: 'Unable to connect. Please refresh the page.',
        severity: 'error'
      });
    }
  }
  
  private handleVoicePermissionError() {
    this.onUIUpdate?.({
      type: 'permission_error',
      message: 'Microphone access denied. Please enable microphone permissions to use voice features.',
      severity: 'warning',
      action: {
        text: 'How to enable',
        onClick: () => this.showPermissionGuide?.()
      }
    });
  }
  
  private handleBudgetError(error: any) {
    this.onUIUpdate?.({
      type: 'budget_error',
      message: `Budget limit reached: $${error.budget_limit}. Some features may be limited.`,
      severity: 'error',
      persistent: true
    });
  }
  
  // Event callbacks
  onUIUpdate?: (update: UIErrorUpdate) => void;
  onRetryConnection?: () => void;
  showPermissionGuide?: () => void;
}
```

### Graceful Degradation Strategies
```typescript
class FeatureManager {
  private features = {
    voice: false,
    websocket: false,
    agents: false,
    streaming: false
  };
  
  async initializeFeatures() {
    // Test WebSocket connectivity
    try {
      await this.testWebSocketConnection();
      this.features.websocket = true;
    } catch (error) {
      console.warn('WebSocket unavailable, falling back to HTTP polling');
      this.setupHTTPPolling();
    }
    
    // Test voice capabilities
    try {
      await this.testVoiceCapabilities();
      this.features.voice = true;
    } catch (error) {
      console.warn('Voice features unavailable, using text-only mode');
      this.features.voice = false;
    }
    
    // Test agent service
    try {
      await this.testAgentService();
      this.features.agents = true;
    } catch (error) {
      console.error('Agent service unavailable');
      this.showFallbackMessage();
    }
    
    this.onFeaturesInitialized?.(this.features);
  }
  
  private async testVoiceCapabilities(): Promise<void> {
    if (!navigator.mediaDevices?.getUserMedia) {
      throw new Error('getUserMedia not supported');
    }
    
    // Test microphone access (will prompt user)
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    stream.getTracks().forEach(track => track.stop());
    
    // Test audio playback
    const audio = new Audio();
    if (!audio.canPlayType('audio/mp3') && !audio.canPlayType('audio/wav')) {
      throw new Error('Audio playback not supported');
    }
  }
  
  private async testAgentService(): Promise<void> {
    const response = await fetch('http://localhost:8001/health', {
      method: 'GET',
      timeout: 5000
    });
    
    if (!response.ok) {
      throw new Error(`Agent service unavailable: ${response.status}`);
    }
  }
  
  onFeaturesInitialized?: (features: any) => void;
}
```

## 🧪 TESTING AND DEVELOPMENT

### Testing Strategy
```typescript
// Unit Tests
describe('WebSocketManager', () => {
  test('connects successfully', async () => {
    const manager = new WebSocketManager('test-session');
    const connected = await manager.connect();
    expect(connected).toBe(true);
  });
  
  test('handles connection failure gracefully', async () => {
    // Mock failed connection
    global.WebSocket = jest.fn().mockImplementation(() => {
      throw new Error('Connection failed');
    });
    
    const manager = new WebSocketManager('test-session');
    const connected = await manager.connect();
    expect(connected).toBe(false);
  });
});

// Integration Tests
describe('Voice Integration', () => {
  test('records and processes audio', async () => {
    const audioManager = new AudioRecordingManager();
    await audioManager.initializeAudio();
    
    const recordingPromise = new Promise((resolve) => {
      audioManager.onRecordingComplete = resolve;
    });
    
    audioManager.startRecording();
    setTimeout(() => audioManager.stopRecording(), 1000);
    
    const base64Audio = await recordingPromise;
    expect(base64Audio).toMatch(/^[A-Za-z0-9+/]+=*$/);
  });
});

// E2E Tests
describe('Complete Workflow', () => {
  test('end-to-end conversation flow', async () => {
    // 1. Connect to WebSocket
    const ws = new WebSocketManager('e2e-test');
    await ws.connect();
    
    // 2. Send text message
    const responsePromise = new Promise((resolve) => {
      ws.onAgentResponse = resolve;
    });
    
    ws.sendTextMessage('Hello, can you help me?');
    
    // 3. Verify response
    const response = await responsePromise;
    expect(response.message).toBeTruthy();
    expect(response.agent_id).toBeTruthy();
  });
});
```

### Development Environment Setup
```bash
# 1. Clone and setup backend
git clone <repository>
cd agents
cp .env.example .env
# Edit .env with your API keys

# 2. Start backend services
docker-compose up -d

# 3. Verify services are running
curl http://localhost:8000/health  # WebSocket service
curl http://localhost:8001/health  # Agent service  
curl http://localhost:8002/health  # Voice service

# 4. Create frontend project
npx create-react-app jarvis-frontend --template typescript
cd jarvis-frontend

# 5. Install additional dependencies
npm install --save-dev @types/node
```

### Browser Compatibility
- **Chrome/Chromium**: Full support (recommended)
- **Firefox**: Full support with slight audio differences
- **Safari**: Limited WebRTC support, voice features may be reduced
- **Edge**: Full support on Chromium-based versions
- **Mobile**: Limited voice features due to browser restrictions

### Performance Considerations
```typescript
// Optimize WebSocket message handling
const messageQueue = new Map<string, any>();
const batchProcessor = setInterval(() => {
  if (messageQueue.size > 0) {
    processBatchedMessages(Array.from(messageQueue.values()));
    messageQueue.clear();
  }
}, 100); // Process every 100ms

// Optimize audio processing
const audioWorker = new Worker('/audio-processor-worker.js');
audioWorker.postMessage({ audioData, command: 'process' });

// Optimize rendering with React.memo and useMemo
const ChatMessage = React.memo(({ message }) => {
  const formattedTime = useMemo(() => 
    formatTime(message.timestamp), [message.timestamp]
  );
  
  return (
    <div className="message">
      <span>{message.content}</span>
      <small>{formattedTime}</small>
    </div>
  );
});
```

## 🎨 UI/UX IMPLEMENTATION GUIDE

### Voice Interaction States & Visual Feedback
```typescript
enum VoiceState {
  IDLE = "idle",           // Ready to receive voice input
  LISTENING = "listening", // Recording user speech
  PROCESSING = "processing", // STT conversion in progress  
  THINKING = "thinking",   // Agent processing request
  SPEAKING = "speaking"    // TTS playback active
}

interface UIFeedback {
  voiceState: VoiceState;
  audioLevel: number;      // 0-1 for waveform visualization
  agentTyping: boolean;    // Show typing indicator
  connectionStatus: "connected" | "reconnecting" | "disconnected";
  budgetStatus: "safe" | "warning" | "critical";
}

// Visual feedback components
const VoiceStateIndicator = ({ state, audioLevel }: any) => {
  const getStateColor = () => {
    switch (state) {
      case VoiceState.LISTENING: return "#ff4444";
      case VoiceState.PROCESSING: return "#ffaa00";
      case VoiceState.THINKING: return "#00aaff";
      case VoiceState.SPEAKING: return "#44ff44";
      default: return "#888888";
    }
  };
  
  return (
    <div className="voice-indicator">
      <div 
        className="mic-icon" 
        style={{ 
          color: getStateColor(),
          transform: `scale(${1 + audioLevel * 0.5})`
        }}
      >
        🎤
      </div>
      <span className="state-text">{state}</span>
    </div>
  );
};

const AudioWaveform = ({ audioLevel, isRecording }: any) => {
  const bars = Array.from({ length: 20 }, (_, i) => (
    <div
      key={i}
      className="waveform-bar"
      style={{
        height: isRecording 
          ? `${Math.random() * audioLevel * 100 + 10}%`
          : '10%',
        backgroundColor: isRecording ? '#ff4444' : '#888888'
      }}
    />
  ));
  
  return <div className="waveform">{bars}</div>;
};
```

### Cost Monitoring UI
```typescript
const CostMeter = ({ costSummary }: { costSummary: CostSummary }) => {
  const percentage = (costSummary.sessionCost / costSummary.budgetLimit) * 100;
  const getColor = () => {
    if (percentage > 90) return "#ff4444";
    if (percentage > 75) return "#ffaa00";
    return "#44ff44";
  };
  
  return (
    <div className="cost-meter">
      <div className="cost-bar">
        <div 
          className="cost-fill"
          style={{ 
            width: `${Math.min(percentage, 100)}%`,
            backgroundColor: getColor()
          }}
        />
      </div>
      <span className="cost-text">
        ${costSummary.sessionCost.toFixed(3)} / ${costSummary.budgetLimit}
      </span>
      {percentage > 90 && (
        <div className="budget-warning">⚠️ Budget limit approaching!</div>
      )}
    </div>
  );
};
```

### Accessibility Implementation
```typescript
// Keyboard shortcuts
const useKeyboardShortcuts = () => {
  useEffect(() => {
    const handleKeyPress = (event: KeyboardEvent) => {
      // Space bar to toggle voice recording
      if (event.code === 'Space' && !event.target.matches('input, textarea')) {
        event.preventDefault();
        toggleVoiceRecording();
      }
      
      // Ctrl+Enter to send message
      if (event.ctrlKey && event.key === 'Enter') {
        sendCurrentMessage();
      }
      
      // Escape to stop any current operation
      if (event.key === 'Escape') {
        stopAllOperations();
      }
    };
    
    document.addEventListener('keydown', handleKeyPress);
    return () => document.removeEventListener('keydown', handleKeyPress);
  }, []);
};

// Screen reader support
const AccessibleMessage = ({ message }: { message: ChatMessage }) => (
  <div 
    role="article"
    aria-label={`Message from ${message.type === 'user' ? 'you' : message.agentName}`}
    aria-describedby={`msg-${message.id}-details`}
  >
    <div className="message-content">
      {message.content}
    </div>
    <div 
      id={`msg-${message.id}-details`}
      className="sr-only"
    >
      Sent at {message.timestamp.toLocaleString()}.
      {message.cost && ` Cost: $${message.cost.toFixed(4)}.`}
      {message.processingTime && ` Processing time: ${message.processingTime}ms.`}
    </div>
  </div>
);
```

## 🚀 DEPLOYMENT AND PRODUCTION SETUP

### Production Environment Variables
```bash
# Production .env
NODE_ENV=production
REACT_APP_WS_URL=wss://your-domain.com/ws
REACT_APP_API_URL=https://your-domain.com/api
REACT_APP_AGENT_SERVICE_URL=https://your-domain.com/agents
REACT_APP_VOICE_SERVICE_URL=https://your-domain.com/voice

# Optional: Feature flags
REACT_APP_ENABLE_VOICE=true
REACT_APP_ENABLE_STREAMING=true
REACT_APP_ENABLE_DEBUG=false
```

### Build Optimization
```typescript
// webpack.config.js optimizations
module.exports = {
  optimization: {
    splitChunks: {
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /[\\/]node_modules[\\/]/,
          name: 'vendors',
          chunks: 'all',
        },
        voice: {
          test: /[\\/]src[\\/]voice[\\/]/,
          name: 'voice',
          chunks: 'all',
        }
      }
    }
  }
};

// Lazy loading for voice features
const VoiceRecorder = lazy(() => import('./components/VoiceRecorder'));
const AudioPlayer = lazy(() => import('./components/AudioPlayer'));

// Service worker for offline support
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js')
    .then(registration => console.log('SW registered'))
    .catch(error => console.log('SW registration failed'));
}
```

## 📋 FINAL IMPLEMENTATION CHECKLIST

### Essential Features
- [ ] WebSocket connection with auto-reconnect
- [ ] Text message sending/receiving  
- [ ] Agent response display with metadata
- [ ] Cost tracking and budget warnings
- [ ] Basic error handling and user feedback
- [ ] Connection status indicators

### Voice Features  
- [ ] Microphone access request
- [ ] Audio recording with WAV encoding
- [ ] Voice activity detection
- [ ] STT integration via voice service
- [ ] TTS audio playback
- [ ] Audio waveform visualization
- [ ] Voice state indicators

### Advanced Features
- [ ] Agent selection interface
- [ ] Session history and persistence
- [ ] Settings panel for voice/agent preferences  
- [ ] Real-time system health monitoring
- [ ] Performance metrics dashboard
- [ ] Keyboard shortcuts and accessibility
- [ ] Mobile-responsive design

### Production Readiness
- [ ] Error boundaries and graceful degradation
- [ ] Loading states and skeleton screens
- [ ] Comprehensive testing suite
- [ ] Performance optimization
- [ ] Security headers and CSP
- [ ] Analytics and monitoring integration

## 🔗 QUICK START SUMMARY

1. **Backend Setup**: `docker-compose up -d` (requires API keys in .env)
2. **Service Verification**: Check all health endpoints are responding
3. **Frontend Initialization**: Create React app with TypeScript template
4. **Core Integration**: Implement WebSocketManager and basic chat UI
5. **Voice Integration**: Add AudioRecordingManager and playback
6. **Testing**: Verify full conversation flow with voice and text
7. **Production**: Add error handling, optimization, and monitoring

## 📞 SUPPORT AND TROUBLESHOOTING

### Common Issues
- **WebSocket connection fails**: Check CORS settings and firewall
- **Voice not working**: Verify microphone permissions and HTTPS
- **High costs**: Implement proper budget controls and monitoring
- **Slow responses**: Check agent service health and model availability

### Debug Endpoints
```bash
# System health
curl http://localhost:8000/health
curl http://localhost:8001/status  
curl http://localhost:8002/metrics

# Connection info
curl http://localhost:8000/connections

# Test voice processing
curl -X POST http://localhost:8002/stt -d '{"audio_data":"test","session_id":"debug"}'
```

---

**This documentation provides everything needed to build a complete frontend that integrates with the Jarvis multi-agent AI system. The backend is production-ready with real-time WebSocket communication, multi-agent orchestration, and comprehensive voice processing capabilities.**