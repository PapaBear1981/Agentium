<template>
  <div class="flex flex-col h-full bg-background">

    <!-- Messages Area -->
    <div 
      ref="messagesContainer"
      class="flex-1 overflow-y-auto px-6 py-4 space-y-4"
    >
      <!-- Welcome Message -->
      <div v-if="messages.length === 0" class="text-center py-12">
        <div class="max-w-md mx-auto">
          <MessageCircle class="w-12 h-12 mx-auto mb-4 text-muted-foreground" />
          <h3 class="text-lg font-medium mb-2">Welcome to Agentium</h3>
          <p class="text-muted-foreground mb-4">
            Start a conversation with our AI agents. You can type a message or use voice input.
          </p>
          <div class="flex flex-wrap gap-2 justify-center">
            <Button
              v-for="suggestion in suggestions"
              :key="suggestion"
              variant="outline"
              size="sm"
              @click="sendSuggestion(suggestion)"
            >
              {{ suggestion }}
            </Button>
          </div>
        </div>
      </div>

      <!-- Chat Messages -->
      <ChatMessage
        v-for="message in messages"
        :key="message.id"
        :message="message"
        @play-audio="playAudio"
      />

      <!-- Typing Indicator -->
      <TypingIndicator
        :is-visible="isTyping"
        :agent-name="currentAgentName"
      />

      <!-- Scroll Anchor -->
      <div ref="scrollAnchor" />
    </div>

    <!-- Chat Input -->
    <ChatInput
      :disabled="!isConnected || isTyping"
      :voice-enabled="voiceEnabled"
      :is-recording="isRecording"
      :is-listening="isListening"
      :audio-level="audioLevel"
      @send-message="sendMessage"
      @start-voice="startVoiceInput"
      @stop-voice="stopVoiceInput"
      @file-upload="handleFileUpload"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAgentium } from '@/composables/useAgentium'
import { useVoiceProcessing } from '@/composables/useVoiceProcessing'
import { cn, formatCost } from '@/lib/utils'
import type { ChatMessage as ChatMessageType } from '@/types'

import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'
import TypingIndicator from './TypingIndicator.vue'
import { MessageCircle } from 'lucide-vue-next'

const store = useAppStore()
const agentium = useAgentium()
const voice = useVoiceProcessing()

const messagesContainer = ref<HTMLElement>()
const scrollAnchor = ref<HTMLElement>()

// Computed properties from store
const messages = computed(() => store.messages)
const isConnected = computed(() => store.isConnected)
const isTyping = computed(() => store.isTyping)
const currentAgentName = computed(() => store.activeAgent?.name || 'AI Assistant')
const costSummary = computed(() => store.costSummary)
const voiceEnabled = computed(() => store.voiceEnabled)
const isRecording = computed(() => voice.isRecording.value)
const isListening = computed(() => voice.vad.state.value.isListening)
const audioLevel = computed(() => voice.audioLevel.value)

const connectionStatus = computed(() => {
  if (store.isConnected) return 'connected'
  if (store.reconnectAttempts > 0) return 'connecting'
  return 'disconnected'
})

const suggestions = [
  'Hello! How can you help me?',
  'What can you do?',
  'Explain quantum computing',
  'Help me write code',
  'Analyze this data'
]

// Initialize systems
onMounted(async () => {
  await agentium.initialize()
  
  if (store.voiceEnabled) {
    await voice.initialize()
  }

  // Set up voice callbacks
  voice.setCallbacks({
    onVoiceMessage: (audioData: string) => {
      agentium.sendVoice(audioData).catch(error => {
        console.error('Failed to send voice message:', error)
      })
    },
    onError: (error: string) => {
      console.error('Voice error:', error)
    }
  })
})

const sendMessage = async (text: string) => {
  try {
    await agentium.sendMessage(text)
    scrollToBottom()
  } catch (error) {
    console.error('Failed to send message:', error)
  }
}

const sendSuggestion = (suggestion: string) => {
  sendMessage(suggestion)
}

const startVoiceInput = async () => {
  if (!voice.canRecord.value) {
    console.warn('Cannot start voice input: not ready')
    return
  }

  try {
    await voice.startListening()
  } catch (error) {
    console.error('Failed to start voice input:', error)
  }
}

const stopVoiceInput = () => {
  voice.stopListening()
}

const playAudio = async (audioData: string) => {
  try {
    await voice.playTTS(audioData)
  } catch (error) {
    console.error('Failed to play audio:', error)
  }
}

const handleFileUpload = (files: FileList) => {
  console.log('Files uploaded:', files)
  // TODO: Implement file upload handling
}

const scrollToBottom = () => {
  nextTick(() => {
    scrollAnchor.value?.scrollIntoView({ behavior: 'smooth' })
  })
}

// Auto-scroll when new messages arrive
watch(messages, () => {
  scrollToBottom()
}, { deep: true })

// Auto-scroll when typing indicator changes
watch(isTyping, () => {
  if (isTyping.value) {
    scrollToBottom()
  }
})
</script>

<style scoped>
/* Custom scrollbar for messages container */
.overflow-y-auto::-webkit-scrollbar {
  width: 6px;
}

.overflow-y-auto::-webkit-scrollbar-track {
  background: transparent;
}

.overflow-y-auto::-webkit-scrollbar-thumb {
  background: hsl(var(--muted-foreground) / 0.3);
  border-radius: 3px;
}

.overflow-y-auto::-webkit-scrollbar-thumb:hover {
  background: hsl(var(--muted-foreground) / 0.5);
}
</style>
