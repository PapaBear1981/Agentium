// WebSocket Message Types
export interface WebSocketMessage {
  type: WebSocketMessageType
  data: any
  timestamp: string
  session_id?: string
  message_id?: string
}

export enum WebSocketMessageType {
  // Client to Server
  VOICE_INPUT = 'voice_input',
  TEXT_INPUT = 'text_input',
  SYSTEM_COMMAND = 'system_command',
  
  // Server to Client
  AGENT_RESPONSE = 'agent_response',
  AGENT_RESPONSE_STREAM = 'agent_response_stream',
  TOOL_EXECUTION = 'tool_execution',
  SYSTEM_STATUS = 'system_status',
  COST_UPDATE = 'cost_update',
  ERROR = 'error',
  
  // Bidirectional
  HEARTBEAT = 'heartbeat',
  CONNECTION_STATUS = 'connection_status'
}

// Voice Processing Types
export interface STTRequest {
  audio_data: string
  format: 'wav' | 'mp3' | 'webm'
  sample_rate: number
  channels: number
  language?: string
  session_id?: string
}

export interface STTResponse {
  text: string
  confidence?: number
  language?: string
  processing_time_ms: number
  provider: 'elevenlabs' | 'whisperx' | 'faster_whisper'
  model: string
  segments?: Array<{
    start: number
    end: number
    text: string
    confidence: number
  }>
  success: boolean
  error?: string
}

export interface TTSRequest {
  text: string
  voice?: string
  language: string
  speed: number
  format: 'wav' | 'mp3'
  session_id?: string
}

export interface TTSResponse {
  audio_data: string
  format: 'wav' | 'mp3'
  sample_rate: number
  duration_ms: number
  processing_time_ms: number
  provider: 'elevenlabs' | 'coqui' | 'pyttsx3'
  voice: string
  success: boolean
  error?: string
}

// Voice States
export enum VoiceState {
  IDLE = 'idle',
  LISTENING = 'listening',
  PROCESSING = 'processing',
  THINKING = 'thinking',
  SPEAKING = 'speaking'
}

export type VoiceStateType = 'idle' | 'listening' | 'processing' | 'thinking' | 'speaking'

// Agent Types
export interface AgentStatus {
  agent_id: string
  name: string
  model: string
  provider: 'openrouter' | 'ollama'
  status: 'active' | 'idle' | 'busy' | 'error'
  tasks_completed: number
  tasks_failed: number
  total_tokens_used: number
  total_cost: number
  average_response_time_ms: number
}

export interface TaskRequest {
  content: string
  session_id: string
  context?: {
    user_level?: string
    preferred_agent?: string
    conversation_history?: Array<any>
  }
  priority: 'low' | 'medium' | 'high' | 'urgent'
}

export interface TaskResponse {
  task_id: string
  result: string
  agent_id: string
  success: boolean
  tokens_used: number
  cost: number
  processing_time_ms: number
  metadata: {
    model: string
    provider: string
    temperature?: number
  }
}

// Chat Types
export interface ChatMessage {
  id: string
  type: 'user' | 'agent' | 'system'
  content: string
  timestamp: Date
  agentId?: string
  agentName?: string
  cost?: number
  tokens?: number
  processingTime?: number
  audioData?: string
  metadata?: any
  files?: FileAttachment[]
}

export interface FileAttachment {
  id: string
  name: string
  size: number
  type: string
  url?: string
  content?: string
  preview?: string
}

// Application State Types
export interface AppState {
  // Connection state
  connected: boolean
  session_id: string
  websocket: WebSocket | null
  reconnectAttempts: number

  // Conversation state
  messages: ChatMessage[]
  currentAgent: string
  conversationHistory: ConversationTurn[]
  
  // Voice state
  recording: boolean
  speaking: boolean
  voiceEnabled: boolean
  voiceState: VoiceState
  audioLevel: number

  // System state
  agents: AgentStatus[]
  systemHealth: SystemHealth
  costSummary: CostSummary
  sessionStats: SessionStats

  // UI state
  sidebarOpen: boolean
  settingsOpen: boolean
  theme: 'light' | 'dark'
  currentView: 'chat' | 'agents' | 'settings'
}

export interface ConversationTurn {
  id: string
  userMessage: string
  agentResponse: string
  timestamp: Date
  cost: number
  processingTime: number
}

export interface SystemHealth {
  overall: 'healthy' | 'degraded' | 'unhealthy'
  services: {
    websocket: boolean
    agents: boolean
    voice: boolean
    database: boolean
  }
  lastCheck: Date
}

export interface CostSummary {
  sessionCost: number
  budgetLimit: number
  budgetRemaining: number
  costBreakdown: Record<string, number>
  lastUpdate: Date
}

export interface SessionStats {
  messagesCount: number
  averageResponseTime: number
  totalTokensUsed: number
  sessionDuration: number
  voiceMinutesUsed: number
}

// Tool Types
export interface ToolExecution {
  tool_name: string
  status: 'started' | 'completed' | 'failed'
  result?: any
  error?: string
  timestamp: Date
}

// Error Types
export interface AppError {
  type: string
  message: string
  timestamp: Date
  context?: any
}

// Settings Types
export interface UserSettings {
  theme: 'light' | 'dark' | 'auto'
  voiceEnabled: boolean
  preferredAgent: string
  budgetLimit: number
  autoPlayTTS: boolean
  voiceActivityDetection: boolean
  notifications: boolean
  language: string
}

export type ThemeType = 'light' | 'dark'

// File Types
export interface FileUpload {
  file: File
  id: string
  progress: number
  status: 'pending' | 'uploading' | 'completed' | 'error'
  error?: string
}

// Chart Types
export interface ChartData {
  type: 'line' | 'bar' | 'pie' | 'doughnut'
  data: any
  options?: any
  title?: string
}

// Calendar Types
export interface CalendarEvent {
  id: string
  title: string
  date: Date
  description?: string
  type: 'reminder' | 'deadline' | 'appointment'
}

// Calculator Types
export interface CalculatorOperation {
  expression: string
  result: number | string
  timestamp: Date
}
