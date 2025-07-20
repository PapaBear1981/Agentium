<template>
  <header class="border-b bg-card px-6 py-4">
    <div class="flex items-center justify-between">
      <!-- Left Section -->
      <div class="flex items-center gap-4">
        <!-- Sidebar Toggle -->
        <Button
          variant="ghost"
          size="icon"
          @click="store.toggleSidebar"
          class="lg:hidden"
        >
          <Menu class="w-5 h-5" />
        </Button>

        <!-- Logo/Title -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
            <Bot class="w-5 h-5 text-primary-foreground" />
          </div>
          <h1 class="text-xl font-bold">Agentium</h1>
        </div>

        <!-- Connection Status -->
        <div class="flex items-center gap-2">
          <div 
            :class="cn(
              'w-2 h-2 rounded-full',
              store.isConnected ? 'bg-green-500' : 'bg-red-500 animate-pulse'
            )"
          />
          <span class="text-sm text-muted-foreground">
            {{ store.isConnected ? 'Connected' : 'Disconnected' }}
          </span>
        </div>
      </div>

      <!-- Center Section - Agent Selector -->
      <div class="flex items-center gap-3">
        <div class="flex items-center gap-2">
          <span class="text-sm text-muted-foreground">Agent:</span>
          <select
            :value="store.currentAgent"
            @change="handleAgentChange"
            class="bg-background border border-input rounded-md px-3 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
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

        <!-- Agent Status -->
        <div v-if="store.activeAgent" class="flex items-center gap-2">
          <div 
            :class="cn(
              'w-2 h-2 rounded-full',
              getAgentStatusColor(store.activeAgent.status)
            )"
          />
          <span class="text-xs text-muted-foreground capitalize">
            {{ store.activeAgent.status }}
          </span>
        </div>
      </div>

      <!-- Right Section -->
      <div class="flex items-center gap-3">
        <!-- Cost Display -->
        <div class="flex items-center gap-2">
          <DollarSign class="w-4 h-4 text-muted-foreground" />
          <div class="text-sm">
            <span class="font-medium">{{ formatCost(store.costSummary.sessionCost) }}</span>
            <span class="text-muted-foreground mx-1">/</span>
            <span class="text-muted-foreground">{{ formatCost(store.costSummary.budgetLimit) }}</span>
          </div>
          
          <!-- Budget Warning -->
          <div 
            v-if="store.budgetStatus === 'warning'"
            class="w-2 h-2 bg-yellow-500 rounded-full animate-pulse"
            title="Budget warning"
          />
          <div 
            v-else-if="store.budgetStatus === 'critical'"
            class="w-2 h-2 bg-red-500 rounded-full animate-pulse"
            title="Budget critical"
          />
        </div>

        <!-- Voice Toggle -->
        <Button
          variant="ghost"
          size="icon"
          @click="toggleVoice"
          :class="{
            'text-primary': store.voiceEnabled,
            'text-muted-foreground': !store.voiceEnabled
          }"
        >
          <Mic class="w-4 h-4" />
        </Button>

        <!-- View Selector -->
        <div class="flex bg-muted rounded-lg p-1">
          <Button
            v-for="view in views"
            :key="view.id"
            :variant="store.currentView === view.id ? 'default' : 'ghost'"
            size="sm"
            @click="store.setCurrentView(view.id)"
            class="h-8 px-3"
          >
            <component :is="view.icon" class="w-4 h-4 mr-2" />
            {{ view.label }}
          </Button>
        </div>

        <!-- Clear Chat Button -->
        <Button
          v-if="store.currentView === 'chat' && store.messages.length > 0"
          variant="ghost"
          size="sm"
          @click="clearChat"
          class="text-muted-foreground hover:text-foreground"
        >
          <Trash2 class="w-4 h-4 mr-2" />
          Clear
        </Button>

        <!-- Settings -->
        <Button
          variant="ghost"
          size="icon"
          @click="store.toggleSettings"
        >
          <Settings class="w-4 h-4" />
        </Button>
      </div>
    </div>
  </header>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { cn, formatCost } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'
import {
  Menu,
  Bot,
  DollarSign,
  Mic,
  Settings,
  MessageSquare,
  Users,
  Cog,
  Trash2
} from 'lucide-vue-next'

const store = useAppStore()

const views = [
  { id: 'chat' as const, label: 'Chat', icon: MessageSquare },
  { id: 'agents' as const, label: 'Agents', icon: Users },
  { id: 'settings' as const, label: 'Settings', icon: Cog }
]

const handleAgentChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  store.setCurrentAgent(target.value)
}

const toggleVoice = () => {
  store.updateUserSettings({ voiceEnabled: !store.voiceEnabled })
}

const clearChat = () => {
  store.clearMessages()
}

const getAgentStatusColor = (status: string) => {
  switch (status) {
    case 'active': return 'bg-green-500'
    case 'idle': return 'bg-yellow-500'
    case 'busy': return 'bg-blue-500'
    case 'error': return 'bg-red-500'
    default: return 'bg-gray-500'
  }
}
</script>
