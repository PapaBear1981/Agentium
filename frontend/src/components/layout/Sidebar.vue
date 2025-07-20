<template>
  <!-- Mobile Overlay -->
  <div 
    v-if="isOpen"
    class="fixed inset-0 bg-black/50 z-40 lg:hidden"
    @click="$emit('toggle')"
  />

  <!-- Sidebar -->
  <aside
    :class="cn(
      'fixed lg:relative inset-y-0 left-0 z-50 w-64 bg-card border-r transform transition-transform duration-300 ease-in-out',
      isOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
      !isOpen && 'lg:w-16'
    )"
  >
    <div class="flex flex-col h-full">
      <!-- Sidebar Header -->
      <div class="p-4 border-b">
        <div class="flex items-center justify-between">
          <div v-if="isOpen || !isCollapsed" class="flex items-center gap-3">
            <div class="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
              <Bot class="w-5 h-5 text-primary-foreground" />
            </div>
            <span class="font-semibold">Workspace</span>
          </div>
          
          <Button
            variant="ghost"
            size="icon"
            @click="$emit('toggle')"
            class="lg:hidden"
          >
            <X class="w-4 h-4" />
          </Button>
        </div>
      </div>

      <!-- Navigation -->
      <nav class="flex-1 p-4 space-y-2">
        <!-- Quick Actions -->
        <div class="space-y-2">
          <SidebarItem
            :icon="Plus"
            label="New Chat"
            :collapsed="isCollapsed"
            @click="newChat"
          />
          
          <SidebarItem
            :icon="Search"
            label="Search"
            :collapsed="isCollapsed"
            @click="openSearch"
          />
        </div>

        <div class="border-t pt-4 mt-4">
          <h3 v-if="!isCollapsed" class="text-sm font-medium text-muted-foreground mb-2">
            Recent Conversations
          </h3>
          
          <div class="space-y-1">
            <SidebarItem
              v-for="conversation in recentConversations"
              :key="conversation.id"
              :icon="MessageSquare"
              :label="conversation.title"
              :collapsed="isCollapsed"
              @click="loadConversation(conversation.id)"
            />
          </div>
        </div>

        <div class="border-t pt-4 mt-4">
          <h3 v-if="!isCollapsed" class="text-sm font-medium text-muted-foreground mb-2">
            Agents
          </h3>
          
          <div class="space-y-1">
            <SidebarItem
              v-for="agent in store.agents"
              :key="agent.agent_id"
              :icon="Bot"
              :label="agent.name"
              :collapsed="isCollapsed"
              :active="store.currentAgent === agent.agent_id"
              @click="selectAgent(agent.agent_id)"
            >
              <template #trailing>
                <div 
                  :class="cn(
                    'w-2 h-2 rounded-full',
                    getAgentStatusColor(agent.status)
                  )"
                />
              </template>
            </SidebarItem>
          </div>
        </div>

        <div class="border-t pt-4 mt-4">
          <h3 v-if="!isCollapsed" class="text-sm font-medium text-muted-foreground mb-2">
            Tools
          </h3>
          
          <div class="space-y-1">
            <SidebarItem
              :icon="Calculator"
              label="Calculator"
              :collapsed="isCollapsed"
              @click="openTool('calculator')"
            />
            
            <SidebarItem
              :icon="Calendar"
              label="Calendar"
              :collapsed="isCollapsed"
              @click="openTool('calendar')"
            />
            
            <SidebarItem
              :icon="BarChart3"
              label="Charts"
              :collapsed="isCollapsed"
              @click="openTool('charts')"
            />
            
            <SidebarItem
              :icon="FileText"
              label="Files"
              :collapsed="isCollapsed"
              @click="openTool('files')"
            />
          </div>
        </div>
      </nav>

      <!-- Sidebar Footer -->
      <div class="p-4 border-t">
        <div v-if="!isCollapsed" class="space-y-3">
          <!-- System Health -->
          <div class="flex items-center gap-2 text-sm">
            <div 
              :class="cn(
                'w-2 h-2 rounded-full',
                store.systemHealth.overall === 'healthy' ? 'bg-green-500' :
                store.systemHealth.overall === 'degraded' ? 'bg-yellow-500' :
                'bg-red-500'
              )"
            />
            <span class="text-muted-foreground">
              System {{ store.systemHealth.overall }}
            </span>
          </div>

          <!-- Session Stats -->
          <div class="text-xs text-muted-foreground space-y-1">
            <div>Messages: {{ store.sessionStats.messagesCount }}</div>
            <div>Tokens: {{ store.sessionStats.totalTokensUsed }}</div>
            <div>Cost: {{ formatCost(store.costSummary.sessionCost) }}</div>
          </div>
        </div>

        <!-- Collapse Toggle (Desktop) -->
        <Button
          variant="ghost"
          size="icon"
          @click="toggleCollapse"
          class="hidden lg:flex w-full justify-center"
        >
          <ChevronLeft v-if="!isCollapsed" class="w-4 h-4" />
          <ChevronRight v-else class="w-4 h-4" />
        </Button>
      </div>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useAppStore } from '@/stores/app'
import { cn, formatCost } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'
import SidebarItem from './SidebarItem.vue'
import { 
  Bot, 
  X, 
  Plus, 
  Search, 
  MessageSquare, 
  Calculator, 
  Calendar, 
  BarChart3, 
  FileText,
  ChevronLeft,
  ChevronRight
} from 'lucide-vue-next'

interface Props {
  isOpen: boolean
}

defineProps<Props>()
defineEmits<{
  toggle: []
}>()

const store = useAppStore()
const isCollapsed = ref(false)

// Mock data - would come from store in real app
const recentConversations = ref([
  { id: '1', title: 'Quantum Computing Discussion' },
  { id: '2', title: 'Code Review Session' },
  { id: '3', title: 'Data Analysis Help' }
])

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

const newChat = () => {
  store.clearMessages()
  store.setCurrentView('chat')
}

const openSearch = () => {
  // TODO: Implement search functionality
  console.log('Opening search...')
}

const loadConversation = (id: string) => {
  // TODO: Load conversation from history
  console.log('Loading conversation:', id)
}

const selectAgent = (agentId: string) => {
  store.setCurrentAgent(agentId)
  store.setCurrentView('chat')
}

const openTool = (tool: string) => {
  // TODO: Open tool in modal or sidebar
  console.log('Opening tool:', tool)
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
