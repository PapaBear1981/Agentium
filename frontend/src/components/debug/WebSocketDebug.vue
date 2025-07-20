<template>
  <div class="fixed bottom-4 right-4 bg-card border rounded-lg p-4 max-w-md max-h-96 overflow-y-auto z-50">
    <div class="flex items-center justify-between mb-2">
      <h3 class="text-sm font-medium">WebSocket Debug</h3>
      <Button variant="ghost" size="icon" @click="$emit('close')" class="h-6 w-6">
        <X class="w-4 h-4" />
      </Button>
    </div>
    
    <div class="space-y-2 text-xs">
      <div class="flex items-center gap-2">
        <div :class="cn('w-2 h-2 rounded-full', connectionStatus === 'connected' ? 'bg-green-500' : 'bg-red-500')" />
        <span class="font-medium">{{ connectionStatus }}</span>
        <span class="text-muted-foreground">{{ sessionId }}</span>
      </div>
      
      <div class="border-t pt-2">
        <div class="text-muted-foreground mb-1">Recent Messages:</div>
        <div class="space-y-1 max-h-48 overflow-y-auto">
          <div 
            v-for="(msg, index) in recentMessages" 
            :key="index"
            :class="cn(
              'p-2 rounded text-xs border',
              msg.direction === 'sent' ? 'bg-blue-50 dark:bg-blue-950' : 'bg-green-50 dark:bg-green-950'
            )"
          >
            <div class="flex items-center gap-2 mb-1">
              <span :class="msg.direction === 'sent' ? 'text-blue-600 dark:text-blue-400' : 'text-green-600 dark:text-green-400'">
                {{ msg.direction === 'sent' ? '→' : '←' }}
              </span>
              <span class="font-medium">{{ msg.type }}</span>
              <span class="text-muted-foreground ml-auto">{{ formatTime(msg.timestamp) }}</span>
            </div>
            <div class="text-muted-foreground">
              {{ JSON.stringify(msg.data, null, 2).substring(0, 100) }}{{ JSON.stringify(msg.data).length > 100 ? '...' : '' }}
            </div>
          </div>
        </div>
      </div>
      
      <div class="border-t pt-2">
        <Button variant="outline" size="sm" @click="clearMessages" class="w-full">
          Clear Log
        </Button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAgentium } from '@/composables/useAgentium'
import { cn, formatTime } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'
import { X } from 'lucide-vue-next'

interface DebugMessage {
  direction: 'sent' | 'received'
  type: string
  data: any
  timestamp: Date
}

const emit = defineEmits<{
  close: []
}>()

const store = useAppStore()
const agentium = useAgentium()

const recentMessages = ref<DebugMessage[]>([])
const maxMessages = 10

const connectionStatus = computed(() => store.isConnected ? 'connected' : 'disconnected')
const sessionId = computed(() => store.sessionId?.substring(0, 16) + '...' || 'none')

const addMessage = (direction: 'sent' | 'received', type: string, data: any) => {
  recentMessages.value.unshift({
    direction,
    type,
    data,
    timestamp: new Date()
  })
  
  // Keep only recent messages
  if (recentMessages.value.length > maxMessages) {
    recentMessages.value = recentMessages.value.slice(0, maxMessages)
  }
}

const clearMessages = () => {
  recentMessages.value = []
}

onMounted(() => {
  // Mock message intercepting - in a real implementation, you'd hook into the WebSocket directly
  console.log('[WebSocketDebug] Debug component mounted')
  
  // Listen for store changes that indicate WebSocket activity
  const originalSendMessage = agentium.sendMessage
  agentium.sendMessage = async (...args) => {
    addMessage('sent', 'text_input', { message: args[0], context: args[1] })
    return originalSendMessage(...args)
  }
})
</script>