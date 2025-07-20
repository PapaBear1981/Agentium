import { ref, watch, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useWebSocket } from './useWebSocket'
import type { ChatMessage, WebSocketMessage } from '@/types'
import { generateSessionId, getApiUrl } from '@/lib/utils'

// Create a single, shared instance of the agent logic.
const createAgentiumInstance = () => {
  const store = useAppStore()
  const {
    connect,
    disconnect,
    sendTextMessage,
    sendVoiceMessage,
    sendSystemCommand,
    setCallbacks,
    state: wsState,
    isConnected
  } = useWebSocket(store.sessionId || generateSessionId())

  const isInitialized = ref(false)
  const lastError = ref<string | null>(null)

  // Initialize the connection and set up callbacks
  const initialize = async () => {
    if (isInitialized.value) return

    // Set session ID in store
    if (!store.sessionId) {
      store.setSessionId(wsState.sessionId)
    }

    // Set up WebSocket callbacks
    setCallbacks({
      onConnectionChange: (connected: boolean) => {
        store.setConnected(connected)
        if (connected) {
          store.resetReconnectAttempts()
          lastError.value = null
        } else {
          store.incrementReconnectAttempts()
        }
      },

      onAgentResponse: (data: any) => {
        console.log('[Agentium] Processing agent response:', data)
        
        // Parse cost value (handle string/Decimal from backend)
        const parseCost = (value: any): number => {
          if (typeof value === 'number') return value
          if (typeof value === 'string') {
            const parsed = parseFloat(value)
            return isNaN(parsed) ? 0 : parsed
          }
          return 0
        }

        const message: ChatMessage = {
          id: crypto.randomUUID(),
          type: 'agent',
          content: data.message || data.content || 'No response received', // Backend sends 'message' field
          timestamp: new Date(),
          agentId: data.agent_id || 'unknown',
          agentName: getAgentName(data.agent_id),
          cost: parseCost(data.cost),
          tokens: data.tokens_used || 0,
          processingTime: data.processing_time_ms || 0,
          audioData: data.audio || data.audio_data, // Handle both field names
          metadata: data.metadata || {}
        }

        console.log('[Agentium] Adding message to store:', message)
        store.addMessage(message)
        store.setTyping(false)

        // Update cost summary
        const cost = parseCost(data.cost)
        if (cost > 0) {
          const currentCost = store.costSummary.sessionCost + cost
          store.updateCostSummary({
            sessionCost: currentCost,
            budgetRemaining: store.costSummary.budgetLimit - currentCost
          })
        }

        // Play audio if available and auto-play is enabled
        const audioData = data.audio || data.audio_data
        if (audioData && store.userSettings.autoPlayTTS) {
          playAudio(audioData)
        }
      },

      onCostUpdate: (data: any) => {
        console.log('[Agentium] Processing cost update:', data)
        
        // Parse cost values (handle string/Decimal from backend)
        const parseCost = (value: any): number => {
          if (typeof value === 'number') return value
          if (typeof value === 'string') {
            const parsed = parseFloat(value)
            return isNaN(parsed) ? 0 : parsed
          }
          return 0
        }

        store.updateCostSummary({
          sessionCost: parseCost(data.session_cost),
          budgetRemaining: parseCost(data.budget_remaining),
          budgetLimit: parseCost(data.budget_limit) || store.costSummary.budgetLimit,
          costBreakdown: data.cost_breakdown || {}
        })

        // Show budget warning if needed
        if (data.warning) {
          console.warn('Budget warning:', data.warning)
        }
      },

      onSystemStatus: (data: any) => {
        console.log('[Agentium] Processing system status:', data)
        
        store.updateSystemHealth({
          overall: data.system_health || data.overall || 'healthy',
          services: {
            websocket: true, // We're connected if we're receiving this
            agents: (data.agents_active || 0) > 0,
            voice: data.voice_processing || false,
            database: true // Assume healthy if we're getting status
          }
        })

        // Update agents if provided
        if (data.agents && Array.isArray(data.agents)) {
          store.updateAgents(data.agents)
        }
      },

      onToolExecution: (data: any) => {
        console.log('Tool execution:', data)
        // Handle tool execution updates
        // This could trigger UI updates for specific tools
      },

      onError: (error: any) => {
        console.error('WebSocket error:', error)
        lastError.value = error.message || 'Unknown error'
        store.setTyping(false)
      },

      onMessage: (message: WebSocketMessage) => {
        console.log('WebSocket message:', message.type, message.data)
      }
    })

    // Connect to WebSocket
    const connected = await connect()
    if (connected) {
      isInitialized.value = true
      
      // Request initial system status
      sendSystemCommand('status')
    } else {
      lastError.value = wsState.lastError
    }

    return connected
  }

  // Send a text message to the agents
  const sendMessage = async (text: string, context?: any) => {
    if (!isConnected.value) {
      console.error('[Agentium] Cannot send message: not connected to server')
      throw new Error('Not connected to server')
    }

    console.log('[Agentium] Sending message:', text)

    // Add user message to chat immediately
    const userMessage: ChatMessage = {
      id: crypto.randomUUID(),
      type: 'user',
      content: text,
      timestamp: new Date()
    }
    
    store.addMessage(userMessage)
    store.setTyping(true)

    // Prepare context with proper format for backend
    const messageContext = {
      preferred_agent: store.currentAgent,
      user_settings: store.userSettings,
      ...context
    }

    console.log('[Agentium] Sending with context:', messageContext)

    // Send to server
    const sent = sendTextMessage(text, messageContext)

    if (!sent) {
      console.error('[Agentium] Failed to send message to server')
      store.setTyping(false)
      throw new Error('Failed to send message')
    }

    console.log('[Agentium] Message sent successfully')
    return sent
  }

  // Send voice message
  const sendVoice = async (audioData: string, format = 'wav', sampleRate = 16000) => {
    if (!isConnected.value) {
      throw new Error('Not connected to server')
    }

    if (!store.voiceEnabled) {
      throw new Error('Voice is disabled')
    }

    store.setVoiceState('processing')
    
    const sent = sendVoiceMessage(audioData, format, sampleRate)
    
    if (!sent) {
      store.setVoiceState('idle')
      throw new Error('Failed to send voice message')
    }

    return sent
  }

  // Switch to a different agent
  const switchAgent = (agentId: string) => {
    store.setCurrentAgent(agentId)
    
    // Notify server of agent preference
    sendSystemCommand('set_preferred_agent', { agent_id: agentId })
  }

  // Clear conversation
  const clearConversation = () => {
    store.clearMessages()
    sendSystemCommand('reset')
  }

  // Get agent name from ID
  const getAgentName = (agentId: string): string => {
    const agent = store.agents.find(a => a.agent_id === agentId)
    return agent?.name || agentId
  }

  // Play audio using Web Audio API
  const playAudio = async (base64Audio: string, format = 'mp3') => {
    try {
      store.setSpeaking(true)
      
      const audio = new Audio()
      audio.src = `data:audio/${format};base64,${base64Audio}`
      
      audio.onended = () => {
        store.setSpeaking(false)
        store.setVoiceState('idle')
      }
      
      audio.onerror = (error) => {
        console.error('Audio playback error:', error)
        store.setSpeaking(false)
        store.setVoiceState('idle')
      }
      
      await audio.play()
    } catch (error) {
      console.error('Failed to play audio:', error)
      store.setSpeaking(false)
      store.setVoiceState('idle')
    }
  }

  // Reconnect to server
  const reconnect = async () => {
    disconnect()
    await new Promise(resolve => setTimeout(resolve, 1000))
    return await connect()
  }

  // Health check
  const checkHealth = async () => {
    try {
      const response = await fetch(getApiUrl('/health'))
      const health = await response.json()
      
      store.updateSystemHealth({
        overall: health.status === 'healthy' ? 'healthy' : 'degraded',
        services: {
          websocket: isConnected.value,
          agents: health.agents_active > 0,
          voice: health.voice_available || false,
          database: health.database_connected || false
        }
      })
      
      return health
    } catch (error) {
      console.error('Health check failed:', error)
      store.updateSystemHealth({
        overall: 'unhealthy',
        services: {
          websocket: isConnected.value,
          agents: false,
          voice: false,
          database: false
        }
      })
      return null
    }
  }

  // Watch for connection changes
  watch(isConnected, (connected) => {
    if (connected) {
      // Request fresh system status when reconnected
      setTimeout(() => {
        sendSystemCommand('status')
        checkHealth()
      }, 1000)
    }
  })

  // Auto-initialize on mount
  onMounted(() => {
    initialize()
  })

  return {
    // State
    isInitialized,
    isConnected,
    lastError,
    
    // Methods
    initialize,
    sendMessage,
    sendVoice,
    switchAgent,
    clearConversation,
    playAudio,
    reconnect,
    checkHealth,
    disconnect,
    
    // Utilities
    sessionId: wsState.sessionId
  }
}

let agentiumInstance: ReturnType<typeof createAgentiumInstance> | null = null

export function useAgentium() {
  if (!agentiumInstance) {
    agentiumInstance = createAgentiumInstance()
  }
  return agentiumInstance
}
