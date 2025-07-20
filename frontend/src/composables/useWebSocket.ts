import { ref, reactive, onUnmounted, computed, readonly } from 'vue'
import { WebSocketMessageType } from '@/types'
import type { 
  WebSocketMessage,
  ChatMessage, 
  CostSummary, 
  AgentStatus,
  SystemHealth 
} from '@/types'
import { generateSessionId, getWebSocketUrl } from '@/lib/utils'

// Backend message types (matching Python backend)
interface BackendWebSocketMessage {
  type: string
  data: any
  timestamp: string
  session_id?: string
  message_id?: string
}

interface BackendAgentResponseData {
  agent_id: string
  agent_name: string
  message: string
  audio?: string
  metadata?: any
  tokens_used: number
  cost: string | number // Backend sends as Decimal (string) or number
  model: string
  processing_time_ms?: number
}

interface BackendCostUpdateData {
  session_cost: string | number
  last_operation_cost: string | number
  budget_remaining: string | number
  budget_limit: string | number
  warning?: string
  cost_breakdown?: Record<string, string | number>
}

interface BackendSystemStatusData {
  agents_active: number
  agents_idle?: number
  agents_error?: number
  session_cost: string | number
  budget_remaining: string | number
  voice_processing: boolean
  tools_available?: number
  system_health?: string
  uptime_seconds?: number
}

export interface WebSocketState {
  connected: boolean
  connecting: boolean
  reconnectAttempts: number
  lastError: string | null
  sessionId: string
}

export interface WebSocketCallbacks {
  onMessage?: (message: WebSocketMessage) => void
  onAgentResponse?: (data: any) => void
  onCostUpdate?: (data: CostSummary) => void
  onSystemStatus?: (data: SystemHealth) => void
  onToolExecution?: (data: any) => void
  onError?: (error: any) => void
  onConnectionChange?: (connected: boolean) => void
}

export function useWebSocket(sessionId?: string) {
  const ws = ref<WebSocket | null>(null)
  const state = reactive<WebSocketState>({
    connected: false,
    connecting: false,
    reconnectAttempts: 0,
    lastError: null,
    sessionId: sessionId || generateSessionId()
  })

  const callbacks = ref<WebSocketCallbacks>({})
  const messageQueue = ref<WebSocketMessage[]>([])
  const maxReconnectAttempts = 5
  const reconnectInterval = 1000

  const isConnected = computed(() => state.connected)
  const canReconnect = computed(() => state.reconnectAttempts < maxReconnectAttempts)

  let reconnectTimer: number | null = null
  let heartbeatTimer: number | null = null

  const connect = async (): Promise<boolean> => {
    if (state.connecting || state.connected) {
      return state.connected
    }

    state.connecting = true
    state.lastError = null

    try {
      const wsUrl = getWebSocketUrl(state.sessionId)
      console.log(`[WebSocket] Attempting to connect to: ${wsUrl}`)
      
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        console.log('[WebSocket] Connection established.')
        state.connected = true
        state.connecting = false
        state.reconnectAttempts = 0
        state.lastError = null
        
        callbacks.value.onConnectionChange?.(true)
        
        processMessageQueue()
        startHeartbeat()
      }

      ws.value.onmessage = (event) => {
        try {
          const rawMessage: BackendWebSocketMessage = JSON.parse(event.data)
          console.log(`[WebSocket] Received message: ${rawMessage.type}`, rawMessage)
          handleMessage(rawMessage)
        } catch (error) {
          console.error('[WebSocket] Failed to parse WebSocket message:', error)
          state.lastError = 'Failed to parse message'
        }
      }

      ws.value.onclose = (event) => {
        console.log(`[WebSocket] Disconnected: Code=${event.code}, Reason=${event.reason}`)
        state.connected = false
        state.connecting = false
        
        callbacks.value.onConnectionChange?.(false)
        stopHeartbeat()
        
        if (!event.wasClean && canReconnect.value) {
          attemptReconnect()
        }
      }

      ws.value.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        state.lastError = 'Connection error'
        state.connecting = false
        callbacks.value.onError?.(error)
      }

      return true
    } catch (error) {
      console.error('[WebSocket] Failed to establish connection:', error)
      state.connecting = false
      state.lastError = error instanceof Error ? error.message : 'Unknown error'
      return false
    }
  }

  const disconnect = () => {
    console.log('[WebSocket] Initiating disconnect.')
    if (reconnectTimer) {
      window.clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    
    stopHeartbeat()
    
    if (ws.value) {
      ws.value.close(1000, 'Client disconnect')
      ws.value = null
    }
    
    state.connected = false
    state.connecting = false
    state.reconnectAttempts = 0
    console.log('[WebSocket] Disconnected successfully.')
  }

  const attemptReconnect = () => {
    if (!canReconnect.value) {
      console.warn('[WebSocket] Max reconnection attempts reached. Not attempting further reconnects.')
      state.lastError = 'Max reconnection attempts reached'
      return
    }

    state.reconnectAttempts++
    const delay = reconnectInterval * Math.pow(2, state.reconnectAttempts - 1)
    
    console.log(`[WebSocket] Reconnection attempt ${state.reconnectAttempts} in ${delay}ms...`)
    
    reconnectTimer = window.setTimeout(() => {
      connect()
    }, delay)
  }

  const sendMessage = (type: WebSocketMessageType, data: any): boolean => {
    const message: WebSocketMessage = {
      type,
      data,
      timestamp: new Date().toISOString(),
      session_id: state.sessionId
    }

    if (state.connected && ws.value?.readyState === WebSocket.OPEN) {
      try {
        console.log(`[WebSocket] Sending message: ${type}`, message)
        ws.value.send(JSON.stringify(message))
        return true
      } catch (error) {
        console.error('[WebSocket] Failed to send message:', error)
        state.lastError = 'Failed to send message'
        return false
      }
    } else {
      messageQueue.value.push(message)
      console.warn(`[WebSocket] Message queued (not connected): ${type}. Queue size: ${messageQueue.value.length}`)
      return false
    }
  }

  const processMessageQueue = () => {
    while (messageQueue.value.length > 0 && state.connected) {
      const message = messageQueue.value.shift()
      if (message && ws.value?.readyState === WebSocket.OPEN) {
        try {
          console.log(`[WebSocket] Sending queued message: ${message.type}`)
          ws.value.send(JSON.stringify(message))
        } catch (error) {
          console.error('[WebSocket] Failed to send queued message:', error)
          messageQueue.value.unshift(message) // Put it back
          break
        }
      }
    }
  }

  const handleMessage = (rawMessage: BackendWebSocketMessage) => {
    // Convert backend message to frontend format
    const message: WebSocketMessage = {
      type: rawMessage.type as WebSocketMessageType,
      data: rawMessage.data,
      timestamp: rawMessage.timestamp,
      session_id: rawMessage.session_id,
      message_id: rawMessage.message_id
    }

    callbacks.value.onMessage?.(message)

    switch (message.type) {
      case WebSocketMessageType.AGENT_RESPONSE:
        console.log('[WebSocket] Handling agent_response:', message.data)
        const agentData = message.data as BackendAgentResponseData
        // Normalize the data format for frontend
        const normalizedAgentData = {
          ...agentData,
          cost: typeof agentData.cost === 'string' ? parseFloat(agentData.cost) : agentData.cost,
          content: agentData.message, // Map message to content for compatibility
          audio_data: agentData.audio // Map audio to audio_data for compatibility
        }
        callbacks.value.onAgentResponse?.(normalizedAgentData)
        break
      case WebSocketMessageType.COST_UPDATE:
        console.log('[WebSocket] Handling cost_update:', message.data)
        const costData = message.data as BackendCostUpdateData
        // Normalize cost data
        const normalizedCostData: CostSummary = {
          sessionCost: typeof costData.session_cost === 'string' ? parseFloat(costData.session_cost) : costData.session_cost,
          budgetRemaining: typeof costData.budget_remaining === 'string' ? parseFloat(costData.budget_remaining) : costData.budget_remaining,
          budgetLimit: typeof costData.budget_limit === 'string' ? parseFloat(costData.budget_limit) : costData.budget_limit,
          costBreakdown: costData.cost_breakdown ? Object.fromEntries(
            Object.entries(costData.cost_breakdown).map(([k, v]) => [k, typeof v === 'string' ? parseFloat(v) : v])
          ) : {},
          lastUpdate: new Date()
        }
        callbacks.value.onCostUpdate?.(normalizedCostData)
        break
      case WebSocketMessageType.SYSTEM_STATUS:
        console.log('[WebSocket] Handling system_status:', message.data)
        const statusData = message.data as BackendSystemStatusData
        // Normalize system status data
        const normalizedStatusData: SystemHealth = {
          overall: (statusData.system_health as 'healthy' | 'degraded' | 'unhealthy') || 'healthy',
          services: {
            websocket: true, // We're connected if we're receiving this
            agents: (statusData.agents_active || 0) > 0,
            voice: statusData.voice_processing || false,
            database: true // Assume healthy if we're getting status
          },
          lastCheck: new Date()
        }
        callbacks.value.onSystemStatus?.(normalizedStatusData)
        break
      case WebSocketMessageType.TOOL_EXECUTION:
        console.log('[WebSocket] Handling tool_execution:', message.data)
        callbacks.value.onToolExecution?.(message.data)
        break
      case WebSocketMessageType.ERROR:
        console.error('[WebSocket] Received error message:', message.data)
        callbacks.value.onError?.(message.data)
        state.lastError = message.data.error_message || message.data.message || 'Unknown error received from server'
        break
      case WebSocketMessageType.HEARTBEAT:
        console.log('[WebSocket] Received heartbeat from server.')
        break
      case WebSocketMessageType.CONNECTION_STATUS:
        console.log('[WebSocket] Received connection status:', message.data)
        break
      default:
        console.warn('[WebSocket] Unknown message type received:', message.type, message)
    }
  }

  const startHeartbeat = () => {
    heartbeatTimer = window.setInterval(() => {
      if (state.connected) {
        console.log('[WebSocket] Sending heartbeat.')
        sendMessage(WebSocketMessageType.HEARTBEAT, { timestamp: Date.now() })
      }
    }, 30000) // Send heartbeat every 30 seconds
  }

  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      console.log('[WebSocket] Stopping heartbeat.')
      window.clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // Convenience methods for common message types
  const sendTextMessage = (text: string, context?: any) => {
    console.log('[WebSocket] Preparing to send text message:', text)
    return sendMessage(WebSocketMessageType.TEXT_INPUT, {
      message: text,
      context: context || {}
    })
  }

  const sendVoiceMessage = (audioData: string, format = 'wav', sampleRate = 16000) => {
    console.log('[WebSocket] Preparing to send voice message (audio data length):', audioData.length)
    return sendMessage(WebSocketMessageType.VOICE_INPUT, {
      audio: audioData,
      format,
      sample_rate: sampleRate
    })
  }

  const sendSystemCommand = (command: string, parameters?: any) => {
    console.log('[WebSocket] Preparing to send system command:', command)
    return sendMessage(WebSocketMessageType.SYSTEM_COMMAND, {
      command,
      parameters: parameters || {}
    })
  }

  const setCallbacks = (newCallbacks: Partial<WebSocketCallbacks>) => {
    console.log('[WebSocket] Setting new callbacks.', Object.keys(newCallbacks))
    callbacks.value = { ...callbacks.value, ...newCallbacks }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    disconnect()
  })

  return {
    // State
    state: readonly(state),
    isConnected,
    canReconnect,
    messageQueue: readonly(messageQueue),
    
    // Methods
    connect,
    disconnect,
    sendMessage,
    sendTextMessage,
    sendVoiceMessage,
    sendSystemCommand,
    setCallbacks,
    
    // Utilities
    sessionId: state.sessionId
  }
}
