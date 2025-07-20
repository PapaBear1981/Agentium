<template>
  <div class="flex items-center gap-3 p-3 bg-muted/50 rounded-lg border">
    <!-- Play/Pause Button -->
    <Button
      variant="ghost"
      size="icon"
      class="h-8 w-8"
      @click="togglePlayback"
      :disabled="!audioData"
    >
      <Play v-if="!isPlaying" class="w-4 h-4" />
      <Pause v-else class="w-4 h-4" />
    </Button>

    <!-- Waveform/Progress -->
    <div class="flex-1 relative">
      <div class="h-2 bg-muted rounded-full overflow-hidden">
        <div 
          class="h-full bg-primary transition-all duration-300"
          :style="{ width: `${progress}%` }"
        />
      </div>
      
      <!-- Time Display -->
      <div class="flex justify-between text-xs text-muted-foreground mt-1">
        <span>{{ formatTime(currentTime) }}</span>
        <span>{{ formatTime(duration) }}</span>
      </div>
    </div>

    <!-- Volume Control -->
    <div class="flex items-center gap-2">
      <Button
        variant="ghost"
        size="icon"
        class="h-6 w-6"
        @click="toggleMute"
      >
        <Volume2 v-if="volume > 0.5" class="w-3 h-3" />
        <Volume1 v-else-if="volume > 0" class="w-3 h-3" />
        <VolumeX v-else class="w-3 h-3" />
      </Button>
      
      <input
        type="range"
        min="0"
        max="1"
        step="0.1"
        :value="volume"
        @input="setVolume(($event.target as HTMLInputElement).value)"
        class="w-16 h-1 bg-muted rounded-lg appearance-none cursor-pointer"
      />
    </div>

    <!-- Download Button -->
    <Button
      variant="ghost"
      size="icon"
      class="h-6 w-6"
      @click="downloadAudio"
      :disabled="!audioData"
    >
      <Download class="w-3 h-3" />
    </Button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { downloadFile } from '@/lib/utils'
import Button from '@/components/ui/Button.vue'
import { Play, Pause, Volume2, Volume1, VolumeX, Download } from 'lucide-vue-next'

interface Props {
  audioData: string
  format?: 'mp3' | 'wav'
  autoPlay?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  format: 'mp3',
  autoPlay: false
})

const emit = defineEmits<{
  play: []
  pause: []
  ended: []
  error: [error: string]
}>()

const audio = ref<HTMLAudioElement | null>(null)
const isPlaying = ref(false)
const currentTime = ref(0)
const duration = ref(0)
const volume = ref(1)
const previousVolume = ref(1)

const progress = computed(() => {
  if (duration.value === 0) return 0
  return (currentTime.value / duration.value) * 100
})

const initializeAudio = () => {
  if (!props.audioData) return

  audio.value = new Audio()
  audio.value.src = `data:audio/${props.format};base64,${props.audioData}`
  audio.value.volume = volume.value

  audio.value.addEventListener('loadedmetadata', () => {
    if (audio.value) {
      duration.value = audio.value.duration
    }
  })

  audio.value.addEventListener('timeupdate', () => {
    if (audio.value) {
      currentTime.value = audio.value.currentTime
    }
  })

  audio.value.addEventListener('play', () => {
    isPlaying.value = true
    emit('play')
  })

  audio.value.addEventListener('pause', () => {
    isPlaying.value = false
    emit('pause')
  })

  audio.value.addEventListener('ended', () => {
    isPlaying.value = false
    currentTime.value = 0
    emit('ended')
  })

  audio.value.addEventListener('error', (event) => {
    const error = `Audio error: ${audio.value?.error?.message || 'Unknown error'}`
    console.error(error)
    emit('error', error)
  })

  if (props.autoPlay) {
    audio.value.play().catch(error => {
      console.error('Auto-play failed:', error)
    })
  }
}

const togglePlayback = () => {
  if (!audio.value) return

  if (isPlaying.value) {
    audio.value.pause()
  } else {
    audio.value.play().catch(error => {
      console.error('Playback failed:', error)
      emit('error', error.message)
    })
  }
}

const setVolume = (newVolume: string | number) => {
  const vol = typeof newVolume === 'string' ? parseFloat(newVolume) : newVolume
  volume.value = Math.max(0, Math.min(1, vol))
  
  if (audio.value) {
    audio.value.volume = volume.value
  }
}

const toggleMute = () => {
  if (volume.value > 0) {
    previousVolume.value = volume.value
    setVolume(0)
  } else {
    setVolume(previousVolume.value)
  }
}

const downloadAudio = () => {
  if (!props.audioData) return

  try {
    // Convert base64 to blob
    const byteCharacters = atob(props.audioData)
    const byteNumbers = new Array(byteCharacters.length)
    
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray], { type: `audio/${props.format}` })
    
    // Create download link
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `audio-${Date.now()}.${props.format}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  } catch (error) {
    console.error('Download failed:', error)
    emit('error', 'Failed to download audio')
  }
}

const formatTime = (seconds: number): string => {
  if (isNaN(seconds)) return '0:00'
  
  const mins = Math.floor(seconds / 60)
  const secs = Math.floor(seconds % 60)
  return `${mins}:${secs.toString().padStart(2, '0')}`
}

// Watch for audio data changes
watch(() => props.audioData, () => {
  if (audio.value) {
    audio.value.pause()
    audio.value = null
  }
  initializeAudio()
})

onMounted(() => {
  initializeAudio()
})

onUnmounted(() => {
  if (audio.value) {
    audio.value.pause()
    audio.value = null
  }
})
</script>

<style scoped>
/* Custom range slider styling */
input[type="range"] {
  background: transparent;
  cursor: pointer;
}

input[type="range"]::-webkit-slider-track {
  background: hsl(var(--muted));
  height: 4px;
  border-radius: 2px;
}

input[type="range"]::-webkit-slider-thumb {
  appearance: none;
  height: 12px;
  width: 12px;
  border-radius: 50%;
  background: hsl(var(--primary));
  cursor: pointer;
  margin-top: -4px;
}

input[type="range"]::-moz-range-track {
  background: hsl(var(--muted));
  height: 4px;
  border-radius: 2px;
  border: none;
}

input[type="range"]::-moz-range-thumb {
  height: 12px;
  width: 12px;
  border-radius: 50%;
  background: hsl(var(--primary));
  cursor: pointer;
  border: none;
}
</style>
