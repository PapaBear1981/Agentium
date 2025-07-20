<template>
  <div class="p-6">
    <div class="max-w-2xl mx-auto">
      <h2 class="text-2xl font-bold mb-6">Settings</h2>
      
      <div class="space-y-6">
        <!-- Voice Settings -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Voice Settings</h3>
          
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium">Voice Input</label>
              <input
                type="checkbox"
                :checked="store.userSettings.voiceEnabled"
                @change="updateSetting('voiceEnabled', ($event.target as HTMLInputElement).checked)"
                class="rounded"
              />
            </div>
            
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium">Auto-play TTS</label>
              <input
                type="checkbox"
                :checked="store.userSettings.autoPlayTTS"
                @change="updateSetting('autoPlayTTS', ($event.target as HTMLInputElement).checked)"
                class="rounded"
              />
            </div>
            
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium">Voice Activity Detection</label>
              <input
                type="checkbox"
                :checked="store.userSettings.voiceActivityDetection"
                @change="updateSetting('voiceActivityDetection', ($event.target as HTMLInputElement).checked)"
                class="rounded"
              />
            </div>
          </div>
        </Card>

        <!-- Agent Settings -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Agent Settings</h3>
          
          <div class="space-y-4">
            <div>
              <label class="text-sm font-medium mb-2 block">Preferred Agent</label>
              <select
                :value="store.userSettings.preferredAgent"
                @change="updateSetting('preferredAgent', ($event.target as HTMLSelectElement).value)"
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
          </div>
        </Card>

        <!-- Budget Settings -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Budget Settings</h3>
          
          <div class="space-y-4">
            <div>
              <label class="text-sm font-medium mb-2 block">Budget Limit ($)</label>
              <input
                type="number"
                :value="store.userSettings.budgetLimit"
                @input="updateSetting('budgetLimit', parseFloat(($event.target as HTMLInputElement).value))"
                min="0"
                step="0.01"
                class="w-full bg-background border border-input rounded-md px-3 py-2 text-sm"
              />
            </div>
            
            <div class="text-sm text-muted-foreground">
              Current session cost: {{ formatCost(store.costSummary.sessionCost) }}
            </div>
          </div>
        </Card>

        <!-- Theme Settings -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">Appearance</h3>
          
          <div class="space-y-4">
            <div>
              <label class="text-sm font-medium mb-2 block">Theme</label>
              <select
                :value="store.userSettings.theme"
                @change="updateSetting('theme', ($event.target as HTMLSelectElement).value as 'light' | 'dark' | 'auto')"
                class="w-full bg-background border border-input rounded-md px-3 py-2 text-sm"
              >
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="auto">Auto</option>
              </select>
            </div>
            
            <div class="flex items-center justify-between">
              <label class="text-sm font-medium">Notifications</label>
              <input
                type="checkbox"
                :checked="store.userSettings.notifications"
                @change="updateSetting('notifications', ($event.target as HTMLInputElement).checked)"
                class="rounded"
              />
            </div>
          </div>
        </Card>

        <!-- System Info -->
        <Card class="p-6">
          <h3 class="text-lg font-semibold mb-4">System Information</h3>
          
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span>Session ID:</span>
              <span class="font-mono text-xs">{{ store.sessionId }}</span>
            </div>
            <div class="flex justify-between">
              <span>Messages:</span>
              <span>{{ store.sessionStats.messagesCount }}</span>
            </div>
            <div class="flex justify-between">
              <span>Total Tokens:</span>
              <span>{{ store.sessionStats.totalTokensUsed }}</span>
            </div>
            <div class="flex justify-between">
              <span>Session Cost:</span>
              <span>{{ formatCost(store.costSummary.sessionCost) }}</span>
            </div>
          </div>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { formatCost } from '@/lib/utils'
import Card from '@/components/ui/Card.vue'

const store = useAppStore()

const updateSetting = (key: string, value: any) => {
  store.updateUserSettings({ [key]: value })
}
</script>
