<template>
  <div class="border-t bg-background p-4">
    <!-- File Upload Area -->
    <div 
      v-if="isDragOver"
      class="absolute inset-0 bg-primary/10 border-2 border-dashed border-primary rounded-lg flex items-center justify-center z-10"
    >
      <div class="text-center">
        <Upload class="w-8 h-8 mx-auto mb-2 text-primary" />
        <p class="text-sm font-medium">Drop files here to upload</p>
      </div>
    </div>

    <!-- Input Area -->
    <div class="flex items-end gap-3">
      <!-- File Upload Button -->
      <Button
        variant="ghost"
        size="icon"
        class="mb-2"
        @click="triggerFileUpload"
        :disabled="disabled"
      >
        <Paperclip class="w-4 h-4" />
      </Button>

      <!-- Text Input -->
      <div class="flex-1 relative">
        <textarea
          id="chat-input"
          ref="textareaRef"
          v-model="inputText"
          :placeholder="placeholder"
          :disabled="disabled"
          class="w-full min-h-[44px] max-h-32 px-4 py-3 pr-12 rounded-lg border border-input bg-background text-sm resize-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50 placeholder:text-muted-foreground"
          @keydown="handleKeydown"
          @input="adjustHeight"
        />
        
        <!-- Voice Button -->
        <Button
          variant="ghost"
          size="icon"
          class="absolute right-1 bottom-1 h-8 w-8"
          :class="{
            'voice-pulse': isRecording,
            'text-red-500': isRecording,
            'text-blue-500': isListening
          }"
          @mousedown="startVoiceInput"
          @mouseup="stopVoiceInput"
          @mouseleave="stopVoiceInput"
          :disabled="disabled || !voiceEnabled"
        >
          <Mic class="w-4 h-4" />
        </Button>
      </div>

      <!-- Send Button -->
      <Button
        @click="sendMessage"
        :disabled="!canSend"
        class="mb-2"
      >
        <Send class="w-4 h-4" />
      </Button>
    </div>

    <!-- Voice Activity Indicator -->
    <div v-if="isRecording || isListening" class="mt-3 flex items-center justify-center">
      <div class="flex items-center gap-3 px-4 py-2 bg-muted rounded-full">
        <div class="flex items-center gap-2">
          <div 
            :class="{
              'w-2 h-2 rounded-full animate-pulse': true,
              'bg-red-500': isRecording,
              'bg-blue-500': isListening
            }"
          />
          <span class="text-sm font-medium">
            {{ isRecording ? 'Recording...' : 'Listening...' }}
          </span>
        </div>
        
        <!-- Audio Level Indicator -->
        <div v-if="audioLevel > 0" class="flex items-center gap-1">
          <div 
            v-for="i in 5" 
            :key="i"
            class="waveform-bar w-1 bg-primary rounded-full transition-all duration-150"
            :style="{ 
              height: `${Math.max(4, audioLevel * 20 * (i / 5))}px`,
              '--i': i - 1 
            }"
          />
        </div>
      </div>
    </div>

    <!-- File Upload Input -->
    <input
      ref="fileInputRef"
      type="file"
      multiple
      accept=".pdf,.csv,.txt,.md,.json"
      class="hidden"
      @change="handleFileUpload"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'
import Button from '@/components/ui/Button.vue'
import { Send, Mic, Paperclip, Upload } from 'lucide-vue-next'

interface Props {
  disabled?: boolean
  placeholder?: string
  voiceEnabled?: boolean
  isRecording?: boolean
  isListening?: boolean
  audioLevel?: number
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  placeholder: 'Type a message...',
  voiceEnabled: true,
  isRecording: false,
  isListening: false,
  audioLevel: 0
})

const emit = defineEmits<{
  'send-message': [text: string]
  'start-voice': []
  'stop-voice': []
  'file-upload': [files: FileList]
}>()

const inputText = ref('')
const textareaRef = ref<HTMLTextAreaElement>()
const fileInputRef = ref<HTMLInputElement>()
const isDragOver = ref(false)

const canSend = computed(() => 
  !props.disabled && inputText.value.trim().length > 0
)

const sendMessage = () => {
  if (!canSend.value) return
  
  const text = inputText.value.trim()
  if (text) {
    emit('send-message', text)
    inputText.value = ''
    adjustHeight()
  }
}

const handleKeydown = (event: KeyboardEvent) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    sendMessage()
  }
}

const adjustHeight = () => {
  nextTick(() => {
    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
      textareaRef.value.style.height = `${Math.min(textareaRef.value.scrollHeight, 128)}px`
    }
  })
}

const startVoiceInput = () => {
  if (props.voiceEnabled && !props.disabled) {
    emit('start-voice')
  }
}

const stopVoiceInput = () => {
  if (props.isRecording || props.isListening) {
    emit('stop-voice')
  }
}

const triggerFileUpload = () => {
  fileInputRef.value?.click()
}

const handleFileUpload = (event: Event) => {
  const target = event.target as HTMLInputElement
  if (target.files && target.files.length > 0) {
    emit('file-upload', target.files)
    target.value = '' // Reset input
  }
}

// Drag and drop handlers
const handleDragOver = (event: Event) => {
  const dragEvent = event as DragEvent
  dragEvent.preventDefault()
  isDragOver.value = true
}

const handleDragLeave = (event: Event) => {
  const dragEvent = event as DragEvent
  dragEvent.preventDefault()
  if (!dragEvent.relatedTarget || !(dragEvent.currentTarget as Element).contains(dragEvent.relatedTarget as Node)) {
    isDragOver.value = false
  }
}

const handleDrop = (event: Event) => {
  const dragEvent = event as DragEvent
  dragEvent.preventDefault()
  isDragOver.value = false

  if (dragEvent.dataTransfer?.files && dragEvent.dataTransfer.files.length > 0) {
    emit('file-upload', dragEvent.dataTransfer.files)
  }
}

onMounted(() => {
  // Add drag and drop listeners to the parent container
  const container = textareaRef.value?.closest('.border-t')
  if (container) {
    container.addEventListener('dragover', handleDragOver)
    container.addEventListener('dragleave', handleDragLeave)
    container.addEventListener('drop', handleDrop)
  }
})

onUnmounted(() => {
  const container = textareaRef.value?.closest('.border-t')
  if (container) {
    container.removeEventListener('dragover', handleDragOver)
    container.removeEventListener('dragleave', handleDragLeave)
    container.removeEventListener('drop', handleDrop)
  }
})
</script>

<style scoped>
.voice-pulse {
  position: relative;
}

.voice-pulse::before {
  content: '';
  position: absolute;
  inset: 0;
  border-radius: 50%;
  background: currentColor;
  opacity: 0.3;
  animation: pulse-ring 1.5s cubic-bezier(0.215, 0.61, 0.355, 1) infinite;
}

@keyframes pulse-ring {
  0% {
    transform: scale(1);
    opacity: 0.3;
  }
  100% {
    transform: scale(1.5);
    opacity: 0;
  }
}

.waveform-bar {
  animation: waveform 1s ease-in-out infinite;
}

@keyframes waveform {
  0%, 100% {
    height: 4px;
  }
  50% {
    height: 20px;
  }
}
</style>
