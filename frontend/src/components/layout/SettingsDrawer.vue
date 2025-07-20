<template>
  <!-- Overlay -->
  <div 
    v-if="isOpen"
    class="fixed inset-0 bg-black/50 z-50"
    @click="$emit('close')"
  />

  <!-- Drawer -->
  <div 
    :class="cn(
      'fixed right-0 top-0 h-full w-80 bg-card border-l shadow-lg transform transition-transform duration-300 ease-in-out z-50',
      isOpen ? 'translate-x-0' : 'translate-x-full'
    )"
  >
    <div class="flex flex-col h-full">
      <!-- Header -->
      <div class="flex items-center justify-between p-4 border-b">
        <h2 class="text-lg font-semibold">Quick Settings</h2>
        <Button
          variant="ghost"
          size="icon"
          @click="$emit('close')"
        >
          <X class="w-4 h-4" />
        </Button>
      </div>

      <!-- Content -->
      <div class="flex-1 overflow-y-auto p-4 space-y-6">
        <!-- Voice Controls -->
        <div>
          <h3 class="text-sm font-medium mb-3">Voice</h3>
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-sm">Voice Input</span>
              <input
                type="checkbox"
                :checked="store.userSettings.voiceEnabled"
                @change="updateSetting('voiceEnabled', ($event.target as HTMLInputElement).checked)"
                class="rounded"
              />
            </div>
            
            <div class="flex items-center justify-between">
              <span class="text-sm">Auto-play TTS</span>
              <input
                type="checkbox"
                :checked="store.userSettings.autoPlayTTS"
                @change="updateSetting('autoPlayTTS', ($event.target as HTMLInputElement).checked)"
                class="rounded"
              />
            </div>
          </div>
        </div>

        <!-- Agent Selection -->
        <div>
          <h3 class="text-sm font-medium mb-3">Current Agent</h3>
          <select
            :value="store.currentAgent"
            @change="store.setCurrentAgent(($event.target as HTMLSelectElement).value)"
            class="w-full bg-background border border-input rounded-md px-3 py-2 text-sm"
          >
            <option 
              v-for="agent in store.agents" 
              :key="agent.agent_id"
              :value="agent.agent_id"
            >
              {{ agent.name }}
            </option>
          </select>
        </div>

        <!-- Budget Monitor -->
        <div>
          <h3 class="text-sm font-medium mb-3">Budget</h3>
          <div class="space-y-2">
            <div class="flex justify-between text-sm">
              <span>Used:</span>
              <span>{{ formatCost(store.costSummary.sessionCost) }}</span>
            </div>
            <div class="flex justify-between text-sm">
              <span>Limit:</span>
              <span>{{ formatCost(store.costSummary.budgetLimit) }}</span>
            </div>
            
            <!-- Budget Bar -->
            <div class="w-full bg-muted rounded-full h-2">
              <div 
                class="h-2 rounded-full transition-all duration-300"
                :class="{
                  'bg-green-500': store.budgetPercentage < 75,
                  'bg-yellow-500': store.budgetPercentage >= 75 && store.budgetPercentage < 90,
                  'bg-red-500': store.budgetPercentage >= 90
                }"
                :style="{ width: `${Math.min(store.budgetPercentage, 100)}%` }"
              />
            </div>
            
            <div class="text-xs text-muted-foreground">
              {{ store.budgetPercentage.toFixed(1) }}% used
            </div>
          </div>
        </div>

        <!-- System Status -->
        <div>
          <h3 class="text-sm font-medium mb-3">System Status</h3>
          <div class="space-y-2">
            <div class="flex items-center justify-between text-sm">
              <span>Connection</span>
              <div class="flex items-center gap-2">
                <div 
                  :class="cn(
                    'w-2 h-2 rounded-full',
                    store.isConnected ? 'bg-green-500' : 'bg-red-500'
                  )"
                />
                <span>{{ store.isConnected ? 'Connected' : 'Disconnected' }}</span>
              </div>
            </div>
            
            <div class="flex items-center justify-between text-sm">
              <span>Voice</span>
              <div class="flex items-center gap-2">
                <div 
                  :class="cn(
                    'w-2 h-2 rounded-full',
                    store.systemHealth.services.voice ? 'bg-green-500' : 'bg-red-500'
                  )"
                />
                <span>{{ store.systemHealth.services.voice ? 'Ready' : 'Unavailable' }}</span>
              </div>
            </div>
            
            <div class="flex items-center justify-between text-sm">
              <span>Agents</span>
              <div class="flex items-center gap-2">
                <div 
                  :class="cn(
                    'w-2 h-2 rounded-full',
                    store.systemHealth.services.agents ? 'bg-green-500' : 'bg-red-500'
                  )"
                />
                <span>{{ store.agents.length }} available</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Quick Actions -->
        <div>
          <h3 class="text-sm font-medium mb-3">Quick Actions</h3>
          <div class="space-y-2">
            <Button
              variant="outline"
              size="sm"
              @click="clearChat"
              class="w-full justify-start"
            >
              <Trash2 class="w-4 h-4 mr-2" />
              Clear Chat
            </Button>
            
            <Button
              variant="outline"
              size="sm"
              @click="exportChat"
              class="w-full justify-start"
            >
              <Download class="w-4 h-4 mr-2" />
              Export Chat
            </Button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { cn, formatCost } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'
import { X, Trash2, Download } from 'lucide-vue-next'

interface Props {
  isOpen: boolean
}

defineProps<Props>()
defineEmits<{
  close: []
}>()

const store = useAppStore()

const updateSetting = (key: string, value: any) => {
  store.updateUserSettings({ [key]: value })
}

const clearChat = () => {
  store.clearMessages()
}

const exportChat = () => {
  // TODO: Implement chat export
  console.log('Exporting chat...')
}
</script>
