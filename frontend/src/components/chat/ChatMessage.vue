<template>
  <div 
    :class="cn(
      'flex w-full mb-4 message-fade-in',
      message.type === 'user' ? 'justify-end' : 'justify-start'
    )"
  >
    <div 
      :class="cn(
        'max-w-[80%] rounded-lg px-4 py-3 shadow-sm',
        message.type === 'user' 
          ? 'bg-primary text-primary-foreground ml-4' 
          : 'bg-card text-card-foreground mr-4 border'
      )"
    >
      <!-- Agent Header -->
      <div v-if="message.type === 'agent'" class="flex items-center gap-2 mb-2">
        <div class="flex items-center gap-2">
          <div 
            :class="cn(
              'w-2 h-2 rounded-full',
              getAgentStatusColor(message.agentId)
            )"
          />
          <span class="text-sm font-medium text-muted-foreground">
            {{ message.agentName || message.agentId }}
          </span>
        </div>
        <div v-if="message.cost" class="ml-auto">
          <Badge variant="outline" class="text-xs">
            {{ formatCost(message.cost) }}
          </Badge>
        </div>
      </div>

      <!-- Message Content -->
      <div 
        v-if="message.content"
        :class="cn(
          'prose prose-sm max-w-none',
          message.type === 'user' 
            ? 'prose-invert' 
            : 'dark:prose-invert'
        )"
        v-html="renderedContent"
      />

      <!-- File Attachments -->
      <div v-if="message.files && message.files.length > 0" class="mt-3 space-y-2">
        <div 
          v-for="file in message.files" 
          :key="file.id"
          class="flex items-center gap-2 p-2 bg-muted rounded border"
        >
          <FileIcon class="w-4 h-4" />
          <span class="text-sm">{{ file.name }}</span>
          <span class="text-xs text-muted-foreground ml-auto">
            {{ getFileSize(file.size) }}
          </span>
        </div>
      </div>

      <!-- Audio Player -->
      <div v-if="message.audioData" class="mt-3">
        <AudioPlayer 
          :audio-data="message.audioData"
          :auto-play="false"
          @play="$emit('play-audio', message.audioData)"
        />
      </div>

      <!-- Message Footer -->
      <div class="flex items-center justify-between mt-2 text-xs text-muted-foreground">
        <span>{{ formatTime(message.timestamp) }}</span>
        
        <div class="flex items-center gap-2">
          <span v-if="message.tokens" class="flex items-center gap-1">
            <Zap class="w-3 h-3" />
            {{ message.tokens }}
          </span>
          
          <span v-if="message.processingTime" class="flex items-center gap-1">
            <Clock class="w-3 h-3" />
            {{ formatDuration(message.processingTime) }}
          </span>

          <!-- Copy Button -->
          <Button
            variant="ghost"
            size="icon"
            class="h-6 w-6 hover:bg-muted"
            @click="copyMessage"
          >
            <Copy class="w-3 h-3" />
          </Button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { cn, formatTime, formatCost, formatDuration, getFileSize, copyToClipboard } from '@/lib/utils'
import type { ChatMessage } from '@/types'
import Button from '@/components/ui/Button.vue'
import Badge from '@/components/ui/Badge.vue'
import AudioPlayer from './AudioPlayer.vue'
import { FileIcon, Zap, Clock, Copy } from 'lucide-vue-next'

interface Props {
  message: ChatMessage
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'play-audio': [audioData: string]
}>()

// Configure marked for safe HTML rendering
marked.setOptions({
  breaks: true,
  gfm: true
})

const renderedContent = computed(() => {
  if (!props.message.content) return ''

  try {
    const html = marked(props.message.content) as string
    return DOMPurify.sanitize(html, {
      ALLOWED_TAGS: [
        'p', 'br', 'strong', 'em', 'u', 'code', 'pre',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'ul', 'ol', 'li', 'blockquote',
        'table', 'thead', 'tbody', 'tr', 'th', 'td',
        'a', 'img'
      ],
      ALLOWED_ATTR: ['href', 'src', 'alt', 'title', 'class']
    })
  } catch (error) {
    console.error('Failed to render markdown:', error)
    return props.message.content
  }
})

const getAgentStatusColor = (agentId?: string) => {
  if (!agentId) return 'bg-gray-500'
  
  // This would typically come from the store
  // For now, return a default active color
  return 'bg-green-500'
}

const copyMessage = async () => {
  try {
    await copyToClipboard(props.message.content)
    // Could show a toast notification here
  } catch (error) {
    console.error('Failed to copy message:', error)
  }
}
</script>

<style scoped>
/* Custom prose styling for code blocks */
:deep(.prose pre) {
  @apply bg-muted p-4 rounded-lg overflow-x-auto;
}

:deep(.prose code) {
  @apply bg-muted px-1 py-0.5 rounded text-sm;
}

:deep(.prose table) {
  @apply border-collapse border border-border;
}

:deep(.prose th),
:deep(.prose td) {
  @apply border border-border px-4 py-2;
}

:deep(.prose th) {
  @apply bg-muted font-semibold;
}
</style>
