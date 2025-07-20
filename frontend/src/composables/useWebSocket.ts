import { ref, reactive, onUnmounted, computed, readonly } from 'vue'
import type { 
  WebSocketMessage, 
  WebSocketMessageType, 
  ChatMessage, 
  CostSummary, 
  AgentStatus,
  SystemHealth 
} from '@/types'
import { generateSessionId, getWebSocketUrl } from '@/lib/utils'

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
      console.log(`Connecting to WebSocket: ${wsUrl}`)
      
      ws.value = new WebSocket(wsUrl)

      ws.value.onopen = () => {
        console.log('WebSocket connected')
        state.connected = true
        state.connecting = false
        state.reconnectAttempts = 0
        state.lastError = null
        
        callbacks.value.onConnectionChange?.(true)
        
        // Process queued messages
        processMessageQueue()
        
        // Start heartbeat
        startHeartbeat()
      }

      ws.value.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          handleMessage(message)
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error)
          state.lastError = 'Failed to parse message'
        }
      }

      ws.value.onclose = (event) => {
        console.log('WebSocket disconnected:', event.code, event.reason)
        state.connected = false
        state.connecting = false
        
        callbacks.value.onConnectionChange?.(false)
        stopHeartbeat()
        
        if (!event.wasClean && canReconnect.value) {
          attemptReconnect()
        }
      }

      ws.value.onerror = (error) => {
        console.error('WebSocket error:', error)
        state.lastError = 'Connection error'
        state.connecting = false
        callbacks.value.onError?.(error)
      }

      return true
    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      state.connecting = false
      state.lastError = error instanceof Error ? error.message : 'Unknown error'
      return false
    }
  }

  const disconnect = () => {
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
  }

  const attemptReconnect = () => {
    if (!canReconnect.value) {
      console.log('Max reconnection attempts reached')
      state.lastError = 'Max reconnection attempts reached'
      return
    }

    state.reconnectAttempts++
    const delay = reconnectInterval * Math.pow(2, state.reconnectAttempts - 1)
    
    console.log(`Reconnection attempt ${state.reconnectAttempts} in ${delay}ms`)
    
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
        ws.value.send(JSON.stringify(message))
        return true
      } catch (error) {
        console.error('Failed to send message:', error)
        state.lastError = 'Failed to send message'
        return false
      }
    } else {
      // Queue message for later
      messageQueue.value.push(message)
      console.log('Message queued (not connected):', type)
      return false
    }
  }

  const processMessageQueue = () => {
    while (messageQueue.value.length > 0 && state.connected) {
      const message = messageQueue.value.shift()
      if (message && ws.value?.readyState === WebSocket.OPEN) {
        try {
          ws.value.send(JSON.stringify(message))
        } catch (error) {
          console.error('Failed to send queued message:', error)
          // Re-queue the message
          messageQueue.value.unshift(message)
          break
        }
      }
    }
  }

  const handleMessage = (message: WebSocketMessage) => {
    callbacks.value.onMessage?.(message)

    switch (message.type) {
      case 'agent_response':
        callbacks.value.onAgentResponse?.(message.data)
        break
      case 'cost_update':
        callbacks.value.onCostUpdate?.(message.data)
        break
      case 'system_status':
        callbacks.value.onSystemStatus?.(message.data)
        break
      case 'tool_execution':
        callbacks.value.onToolExecution?.(message.data)
        break
      case 'error':
        callbacks.value.onError?.(message.data)
        state.lastError = message.data.message || 'Unknown error'
        break
      case 'heartbeat':
        // Respond to heartbeat
        sendMessage('heartbeat' as WebSocketMessageType, { timestamp: Date.now() })
        break
      case 'connection_status':
        // Handle connection status updates
        console.log('Connection status:', message.data)
        break
      default:
        console.log('Unknown message type:', message.type)
    }
  }

  const startHeartbeat = () => {
    heartbeatTimer = window.setInterval(() => {
      if (state.connected) {
        sendMessage('heartbeat' as WebSocketMessageType, { timestamp: Date.now() })
      }
    }, 30000) // Send heartbeat every 30 seconds
  }

  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      window.clearInterval(heartbeatTimer)
      heartbeatTimer = null
    }
  }

  // Convenience methods for common message types
  const sendTextMessage = (text: string, context?: any) => {
    return sendMessage('text_input' as WebSocketMessageType, {
      message: text,
      context
    })
  }

  const sendVoiceMessage = (audioData: string, format = 'wav', sampleRate = 16000) => {
    return sendMessage('voice_input' as WebSocketMessageType, {
      audio: audioData,
      format,
      sample_rate: sampleRate
    })
  }

  const sendSystemCommand = (command: string, parameters?: any) => {
    return sendMessage('system_command' as WebSocketMessageType, {
      command,
      parameters
    })
  }

  const setCallbacks = (newCallbacks: Partial<WebSocketCallbacks>) => {
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
