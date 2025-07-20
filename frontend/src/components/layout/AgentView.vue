<template>
  <div class="p-6">
    <div class="max-w-4xl mx-auto">
      <h2 class="text-2xl font-bold mb-6">Agent Management</h2>
      
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card 
          v-for="agent in store.agents" 
          :key="agent.agent_id"
          class="p-6"
        >
          <div class="flex items-center gap-3 mb-4">
            <div 
              :class="cn(
                'w-3 h-3 rounded-full',
                getAgentStatusColor(agent.status)
              )"
            />
            <h3 class="font-semibold">{{ agent.name }}</h3>
          </div>
          
          <div class="space-y-2 text-sm text-muted-foreground">
            <div>Model: {{ agent.model }}</div>
            <div>Provider: {{ agent.provider }}</div>
            <div>Tasks: {{ agent.tasks_completed }}</div>
            <div>Cost: {{ formatCost(agent.total_cost) }}</div>
            <div>Avg Response: {{ agent.average_response_time_ms }}ms</div>
          </div>
          
          <div class="mt-4">
            <Button
              :variant="store.currentAgent === agent.agent_id ? 'default' : 'outline'"
              size="sm"
              @click="selectAgent(agent.agent_id)"
              class="w-full"
            >
              {{ store.currentAgent === agent.agent_id ? 'Active' : 'Select' }}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAppStore } from '@/stores/app'
import { cn, formatCost } from '@/lib/utils'
import Card from '@/components/ui/Card.vue'
import Button from '@/components/ui/Button.vue'

const store = useAppStore()

const selectAgent = (agentId: string) => {
  store.setCurrentAgent(agentId)
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
