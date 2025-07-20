<template>
  <div v-if="isVisible" class="flex justify-start mb-4 message-fade-in">
    <div class="max-w-[80%] rounded-lg px-4 py-3 bg-card text-card-foreground mr-4 border shadow-sm">
      <div class="flex items-center gap-2 mb-2">
        <div class="w-2 h-2 rounded-full bg-blue-500" />
        <span class="text-sm font-medium text-muted-foreground">
          {{ agentName || 'Agent' }} is thinking...
        </span>
      </div>
      
      <div class="typing-indicator">
        <span 
          v-for="i in 3" 
          :key="i"
          class="w-2 h-2 bg-primary rounded-full animate-pulse"
          :style="{ '--i': i - 1, animationDelay: `${(i - 1) * 0.2}s` }"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Props {
  isVisible: boolean
  agentName?: string
}

withDefaults(defineProps<Props>(), {
  isVisible: false
})
</script>

<style scoped>
.typing-indicator {
  @apply flex space-x-1;
}

.typing-indicator span {
  animation: typing-pulse 1.4s ease-in-out infinite;
}

@keyframes typing-pulse {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}
</style>
