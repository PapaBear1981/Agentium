<template>
  <button
    :class="cn(
      'w-full flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors',
      'hover:bg-accent hover:text-accent-foreground',
      'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2',
      active ? 'bg-accent text-accent-foreground' : 'text-muted-foreground',
      collapsed && 'justify-center px-2'
    )"
    @click="$emit('click')"
  >
    <component :is="icon" class="w-4 h-4 flex-shrink-0" />
    
    <span v-if="!collapsed" class="flex-1 text-left truncate">
      {{ label }}
    </span>
    
    <div v-if="!collapsed && $slots.trailing" class="flex-shrink-0">
      <slot name="trailing" />
    </div>
  </button>
</template>

<script setup lang="ts">
import { cn } from '@/lib/utils'
import type { Component } from 'vue'

interface Props {
  icon: Component
  label: string
  active?: boolean
  collapsed?: boolean
}

withDefaults(defineProps<Props>(), {
  active: false,
  collapsed: false
})

defineEmits<{
  click: []
}>()
</script>
