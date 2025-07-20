# Frontend Development Notes - Jarvis Multi-Agent AI System

## WebSocket API Specification

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

## HTTP API Endpoints

### Health & Status
```
GET /health
Response: {
  status: "healthy" | "degraded" | "unhealthy",
  services: {
    database: boolean,
    qdrant: boolean,
    ollama: boolean,
    voice: boolean
  },
  timestamp: string
}

GET /agents/status
Response: {
  agents: [
    {
      id: string,
      name: string,
      model: string,
      status: "active" | "idle" | "error",
      last_activity: string
    }
  ]
}
```

### Tools & Capabilities
```
GET /tools/list
Response: {
  tools: [
    {
      name: string,
      version: string,
      description: string,
      status: "available" | "installing" | "error"
    }
  ]
}

POST /tools/install
Body: { tool_name: string, version?: string }
Response: { status: string, message: string }
```

### Analytics & Costs
```
GET /costs/summary?session_id={id}
Response: {
  total_cost: number,
  breakdown: {
    [agent_id]: {
      model: string,
      tokens: number,
      cost: number
    }
  },
  budget_limit: number,
  budget_remaining: number
}
```

## Frontend Architecture Recommendations

### State Management
```typescript
interface AppState {
  // Connection state
  connected: boolean;
  session_id: string;

  // Conversation state
  messages: Message[];
  current_agent: string;

  // Voice state
  recording: boolean;
  speaking: boolean;
  voice_enabled: boolean;

  // System state
  agents: Agent[];
  tools: Tool[];
  cost_summary: CostSummary;

  // UI state
  sidebar_open: boolean;
  settings_open: boolean;
  theme: "light" | "dark";
}
```

### Component Structure
```
App/
├── Header/
│   ├── ConnectionStatus
│   ├── CostDisplay
│   └── SettingsButton
├── Sidebar/
│   ├── AgentList
│   ├── ToolList
│   └── SessionHistory
├── ChatArea/
│   ├── MessageList
│   ├── VoiceVisualizer
│   └── InputArea
└── Footer/
    ├── VoiceControls
    ├── StatusBar
    └── BudgetWarning
```

## Voice Integration

### Web Audio API Usage
```typescript
// Microphone access
const stream = await navigator.mediaDevices.getUserMedia({
  audio: {
    sampleRate: 16000,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true
  }
});

// Audio recording
const mediaRecorder = new MediaRecorder(stream, {
  mimeType: 'audio/webm;codecs=opus'
});

// Audio playback
const audio = new Audio();
audio.src = `data:audio/wav;base64,${base64Audio}`;
audio.play();
```

### Voice Activity Detection
```typescript
interface VoiceActivityDetector {
  start(): void;
  stop(): void;
  onSpeechStart: () => void;
  onSpeechEnd: () => void;
  threshold: number;
}
```

## Real-time Features

### WebSocket Connection Management
```typescript
class WebSocketManager {
  private ws: WebSocket;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 5;

  connect(sessionId: string): Promise<void>;
  disconnect(): void;
  send(message: WebSocketMessage): void;
  onMessage(callback: (message: WebSocketMessage) => void): void;
  onError(callback: (error: Event) => void): void;
  onClose(callback: (event: CloseEvent) => void): void;
}
```

### Message Streaming
```typescript
// Handle streaming responses
const handleStreamingResponse = (message: WebSocketMessage) => {
  if (message.type === 'agent_response_stream') {
    // Append to current message
    updateCurrentMessage(message.data.chunk);
  } else if (message.type === 'agent_response_complete') {
    // Finalize message
    finalizeCurrentMessage();
  }
};
```

## UI/UX Considerations

### Voice Interaction States
- **Idle**: Ready to receive voice input
- **Listening**: Recording user speech
- **Processing**: STT conversion in progress
- **Thinking**: Agent processing request
- **Speaking**: TTS playback active

### Visual Feedback
- Voice waveform visualization during recording
- Agent typing indicators
- Tool execution progress bars
- Cost meter with budget warnings
- Connection status indicators

### Accessibility
- Keyboard shortcuts for all voice functions
- Screen reader support for all messages
- High contrast mode support
- Adjustable font sizes
- Voice command alternatives

## Error Handling

### Connection Errors
```typescript
enum ConnectionError {
  NETWORK_ERROR = "network_error",
  AUTH_ERROR = "auth_error",
  SERVER_ERROR = "server_error",
  TIMEOUT = "timeout"
}
```

### Voice Errors
```typescript
enum VoiceError {
  MIC_ACCESS_DENIED = "mic_access_denied",
  AUDIO_FORMAT_ERROR = "audio_format_error",
  STT_ERROR = "stt_error",
  TTS_ERROR = "tts_error"
}
```

## Performance Optimization

### Audio Optimization
- Use Web Workers for audio processing
- Implement audio compression before transmission
- Buffer management for smooth playback
- Adaptive quality based on connection

### Message Optimization
- Message batching for high-frequency updates
- Compression for large payloads
- Efficient state updates with immutable data
- Virtual scrolling for long conversations

## Security Considerations

### Authentication
- Session-based authentication
- JWT tokens for API access
- Secure WebSocket connections (WSS)
- API key management

### Data Privacy
- No persistent audio storage on client
- Encrypted message transmission
- User consent for voice processing
- Data retention policies

## Testing Strategy

### Unit Tests
- WebSocket connection handling
- Audio processing functions
- State management logic
- Component rendering

### Integration Tests
- End-to-end voice workflow
- WebSocket message flow
- Error handling scenarios
- Performance under load

### Browser Compatibility
- Chrome/Chromium (primary)
- Firefox support
- Safari compatibility
- Mobile browser testing