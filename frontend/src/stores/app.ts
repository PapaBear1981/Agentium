import { ref, computed, reactive } from 'vue'
import { defineStore } from 'pinia'
import type {
  ChatMessage,
  AgentStatus,
  CostSummary,
  SystemHealth,
  VoiceStateType,
  UserSettings,
  SessionStats,
  ConversationTurn,
  ThemeType
} from '@/types'

export const useAppStore = defineStore('app', () => {
  // Connection State
  const connected = ref(false)
  const sessionId = ref('')
  const reconnectAttempts = ref(0)

  // Chat State
  const messages = ref<ChatMessage[]>([])
  const currentAgent = ref('agent1_openrouter_gpt40')
  const conversationHistory = ref<ConversationTurn[]>([])
  const isTyping = ref(false)

  // Voice State
  const voiceState = ref<VoiceStateType>('idle')
  const recording = ref(false)
  const speaking = ref(false)
  const voiceEnabled = ref(true)
  const audioLevel = ref(0)

  // System State
  const agents = ref<AgentStatus[]>([
    {
      agent_id: 'agent1_openrouter_gpt40',
      name: 'GPT-4 Agent',
      model: 'gpt-4',
      provider: 'openrouter',
      status: 'active',
      tasks_completed: 0,
      tasks_failed: 0,
      total_tokens_used: 0,
      total_cost: 0,
      average_response_time_ms: 0
    },
    {
      agent_id: 'agent2_ollama_llama3',
      name: 'Llama 3 Agent',
      model: 'llama3',
      provider: 'ollama',
      status: 'idle',
      tasks_completed: 0,
      tasks_failed: 0,
      total_tokens_used: 0,
      total_cost: 0,
      average_response_time_ms: 0
    }
  ])
  const systemHealth = ref<SystemHealth>({
    overall: 'healthy',
    services: {
      websocket: false,
      agents: true,
      voice: true,
      database: true
    },
    lastCheck: new Date()
  })

  const costSummary = ref<CostSummary>({
    sessionCost: 0,
    budgetLimit: 100,
    budgetRemaining: 100,
    costBreakdown: {},
    lastUpdate: new Date()
  })

  const sessionStats = ref<SessionStats>({
    messagesCount: 0,
    averageResponseTime: 0,
    totalTokensUsed: 0,
    sessionDuration: 0,
    voiceMinutesUsed: 0
  })

  // UI State
  const sidebarOpen = ref(true) // Open by default on desktop
  const settingsOpen = ref(false)
  const theme = ref<ThemeType>('dark')
  const currentView = ref<'chat' | 'agents' | 'settings'>('chat')

  // User Settings
  const userSettings = ref<UserSettings>({
    theme: 'dark',
    voiceEnabled: true,
    preferredAgent: 'agent1_openrouter_gpt40',
    budgetLimit: 100,
    autoPlayTTS: true,
    voiceActivityDetection: true,
    notifications: true,
    language: 'en'
  })

  // Computed Properties
  const isConnected = computed(() => connected.value)
  const canSendMessage = computed(() => connected.value && !isTyping.value)
  const budgetPercentage = computed(() =>
    (costSummary.value.sessionCost / costSummary.value.budgetLimit) * 100
  )
  const budgetStatus = computed(() => {
    const percentage = budgetPercentage.value
    if (percentage > 90) return 'critical'
    if (percentage > 75) return 'warning'
    return 'safe'
  })

  const activeAgent = computed(() =>
    agents.value.find(agent => agent.agent_id === currentAgent.value)
  )

  const lastMessage = computed(() =>
    messages.value[messages.value.length - 1]
  )

  // Actions
  const setConnected = (status: boolean) => {
    connected.value = status
  }

  const setSessionId = (id: string) => {
    sessionId.value = id
  }

  const addMessage = (message: ChatMessage) => {
    messages.value.push(message)
    sessionStats.value.messagesCount++
  }

  const updateMessage = (id: string, updates: Partial<ChatMessage>) => {
    const index = messages.value.findIndex(msg => msg.id === id)
    if (index !== -1) {
      messages.value[index] = { ...messages.value[index], ...updates }
    }
  }

  const clearMessages = () => {
    messages.value = []
    conversationHistory.value = []
    sessionStats.value.messagesCount = 0
  }

  const setCurrentAgent = (agentId: string) => {
    currentAgent.value = agentId
  }

  const updateAgents = (newAgents: AgentStatus[]) => {
    agents.value = newAgents
  }

  const updateCostSummary = (newCost: Partial<CostSummary>) => {
    costSummary.value = { ...costSummary.value, ...newCost, lastUpdate: new Date() }
  }

  const updateSystemHealth = (newHealth: Partial<SystemHealth>) => {
    systemHealth.value = { ...systemHealth.value, ...newHealth, lastCheck: new Date() }
  }

  const setVoiceState = (state: VoiceStateType) => {
    voiceState.value = state
  }

  const setRecording = (status: boolean) => {
    recording.value = status
  }

  const setSpeaking = (status: boolean) => {
    speaking.value = status
  }

  const setAudioLevel = (level: number) => {
    audioLevel.value = level
  }

  const setTyping = (status: boolean) => {
    isTyping.value = status
  }

  const toggleSidebar = () => {
    sidebarOpen.value = !sidebarOpen.value
  }

  const toggleSettings = () => {
    settingsOpen.value = !settingsOpen.value
  }

  const setCurrentView = (view: 'chat' | 'agents' | 'settings') => {
    currentView.value = view
  }

  const updateUserSettings = (newSettings: Partial<UserSettings>) => {
    userSettings.value = { ...userSettings.value, ...newSettings }

    // Apply theme change immediately
    if (newSettings.theme && newSettings.theme !== 'auto') {
      theme.value = newSettings.theme as ThemeType
      document.documentElement.classList.toggle('dark', newSettings.theme === 'dark')
    } else if (newSettings.theme === 'auto') {
      // Handle auto theme based on system preference
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      theme.value = prefersDark ? 'dark' : 'light'
      document.documentElement.classList.toggle('dark', prefersDark)
    }
  }

  const incrementReconnectAttempts = () => {
    reconnectAttempts.value++
  }

  const resetReconnectAttempts = () => {
    reconnectAttempts.value = 0
  }

  return {
    // State
    connected,
    sessionId,
    reconnectAttempts,
    messages,
    currentAgent,
    conversationHistory,
    isTyping,
    voiceState,
    recording,
    speaking,
    voiceEnabled,
    audioLevel,
    agents,
    systemHealth,
    costSummary,
    sessionStats,
    sidebarOpen,
    settingsOpen,
    theme,
    currentView,
    userSettings,

    // Computed
    isConnected,
    canSendMessage,
    budgetPercentage,
    budgetStatus,
    activeAgent,
    lastMessage,

    // Actions
    setConnected,
    setSessionId,
    addMessage,
    updateMessage,
    clearMessages,
    setCurrentAgent,
    updateAgents,
    updateCostSummary,
    updateSystemHealth,
    setVoiceState,
    setRecording,
    setSpeaking,
    setAudioLevel,
    setTyping,
    toggleSidebar,
    toggleSettings,
    setCurrentView,
    updateUserSettings,
    incrementReconnectAttempts,
    resetReconnectAttempts
  }
})
