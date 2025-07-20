import { ref, computed, onUnmounted, readonly } from 'vue'

export interface AudioPlaybackState {
  isPlaying: boolean
  currentAudio: HTMLAudioElement | null
  volume: number
  duration: number
  currentTime: number
  queue: string[]
  error: string | null
}

export interface PlaybackOptions {
  autoPlay?: boolean
  volume?: number
  format?: 'mp3' | 'wav'
  preload?: boolean
}

export function useAudioPlayback(options: PlaybackOptions = {}) {
  const defaultOptions = {
    autoPlay: true,
    volume: 1.0,
    format: 'mp3' as const,
    preload: true,
    ...options
  }

  const state = ref<AudioPlaybackState>({
    isPlaying: false,
    currentAudio: null,
    volume: defaultOptions.volume,
    duration: 0,
    currentTime: 0,
    queue: [],
    error: null
  })

  const callbacks = ref<{
    onPlaybackStart?: () => void
    onPlaybackEnd?: () => void
    onPlaybackError?: (error: string) => void
    onAudioReady?: (duration: number) => void
    onTimeUpdate?: (currentTime: number, duration: number) => void
  }>({})

  let updateTimer: number | null = null

  const isQueueEmpty = computed(() => state.value.queue.length === 0)
  const hasAudio = computed(() => state.value.currentAudio !== null)
  const progress = computed(() => {
    if (state.value.duration === 0) return 0
    return (state.value.currentTime / state.value.duration) * 100
  })

  const playAudio = async (base64Audio: string, format = defaultOptions.format): Promise<void> => {
    return new Promise((resolve, reject) => {
      try {
        state.value.error = null
        
        // Create new audio element
        const audio = new Audio()
        audio.src = `data:audio/${format};base64,${base64Audio}`
        audio.volume = state.value.volume
        audio.preload = defaultOptions.preload ? 'auto' : 'none'

        // Set up event listeners
        audio.onloadedmetadata = () => {
          state.value.duration = audio.duration
          callbacks.value.onAudioReady?.(audio.duration)
        }

        audio.onloadeddata = () => {
          console.log(`Audio loaded: ${audio.duration}s`)
        }

        audio.onplay = () => {
          state.value.isPlaying = true
          state.value.currentAudio = audio
          callbacks.value.onPlaybackStart?.()
          startTimeUpdates()
        }

        audio.onpause = () => {
          state.value.isPlaying = false
          stopTimeUpdates()
        }

        audio.onended = () => {
          state.value.isPlaying = false
          state.value.currentAudio = null
          state.value.currentTime = 0
          callbacks.value.onPlaybackEnd?.()
          stopTimeUpdates()
          
          // Process next item in queue
          processQueue()
          resolve()
        }

        audio.onerror = (event) => {
          const errorMsg = `Audio playback error: ${audio.error?.message || 'Unknown error'}`
          state.value.error = errorMsg
          state.value.isPlaying = false
          state.value.currentAudio = null
          callbacks.value.onPlaybackError?.(errorMsg)
          stopTimeUpdates()
          reject(new Error(errorMsg))
        }

        audio.ontimeupdate = () => {
          state.value.currentTime = audio.currentTime
          callbacks.value.onTimeUpdate?.(audio.currentTime, audio.duration)
        }

        // Start playback
        if (defaultOptions.autoPlay) {
          audio.play().catch(reject)
        } else {
          resolve()
        }

      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : 'Failed to create audio'
        state.value.error = errorMsg
        callbacks.value.onPlaybackError?.(errorMsg)
        reject(new Error(errorMsg))
      }
    })
  }

  const queueAudio = (base64Audio: string, format = defaultOptions.format) => {
    if (state.value.isPlaying) {
      state.value.queue.push(base64Audio)
      console.log(`Audio queued. Queue length: ${state.value.queue.length}`)
    } else {
      playAudio(base64Audio, format).catch(error => {
        console.error('Failed to play queued audio:', error)
      })
    }
  }

  const processQueue = () => {
    if (state.value.queue.length > 0) {
      const nextAudio = state.value.queue.shift()!
      playAudio(nextAudio).catch(error => {
        console.error('Failed to play next audio in queue:', error)
        // Continue processing queue even if one item fails
        processQueue()
      })
    }
  }

  const stopPlayback = () => {
    if (state.value.currentAudio) {
      state.value.currentAudio.pause()
      state.value.currentAudio.currentTime = 0
      state.value.currentAudio = null
    }
    
    state.value.isPlaying = false
    state.value.currentTime = 0
    stopTimeUpdates()
  }

  const pausePlayback = () => {
    if (state.value.currentAudio && state.value.isPlaying) {
      state.value.currentAudio.pause()
    }
  }

  const resumePlayback = () => {
    if (state.value.currentAudio && !state.value.isPlaying) {
      state.value.currentAudio.play().catch(error => {
        const errorMsg = `Failed to resume playback: ${error.message}`
        state.value.error = errorMsg
        callbacks.value.onPlaybackError?.(errorMsg)
      })
    }
  }

  const setVolume = (volume: number) => {
    const clampedVolume = Math.max(0, Math.min(1, volume))
    state.value.volume = clampedVolume
    
    if (state.value.currentAudio) {
      state.value.currentAudio.volume = clampedVolume
    }
  }

  const seekTo = (time: number) => {
    if (state.value.currentAudio) {
      const clampedTime = Math.max(0, Math.min(state.value.duration, time))
      state.value.currentAudio.currentTime = clampedTime
      state.value.currentTime = clampedTime
    }
  }

  const clearQueue = () => {
    state.value.queue = []
  }

  const skipCurrent = () => {
    if (state.value.isPlaying) {
      stopPlayback()
      processQueue()
    }
  }

  const startTimeUpdates = () => {
    if (updateTimer) return
    
    updateTimer = window.setInterval(() => {
      if (state.value.currentAudio && state.value.isPlaying) {
        state.value.currentTime = state.value.currentAudio.currentTime
      }
    }, 100) // Update every 100ms
  }

  const stopTimeUpdates = () => {
    if (updateTimer) {
      window.clearInterval(updateTimer)
      updateTimer = null
    }
  }

  const setCallbacks = (newCallbacks: Partial<typeof callbacks.value>) => {
    callbacks.value = { ...callbacks.value, ...newCallbacks }
  }

  // Test audio playback capability
  const testPlayback = async (): Promise<boolean> => {
    try {
      const audio = new Audio()
      const canPlayMp3 = audio.canPlayType('audio/mp3') !== ''
      const canPlayWav = audio.canPlayType('audio/wav') !== ''
      
      if (!canPlayMp3 && !canPlayWav) {
        throw new Error('Browser does not support audio playback')
      }
      
      return true
    } catch (error) {
      const errorMsg = error instanceof Error ? error.message : 'Audio test failed'
      state.value.error = errorMsg
      callbacks.value.onPlaybackError?.(errorMsg)
      return false
    }
  }

  // Cleanup
  const cleanup = () => {
    stopPlayback()
    clearQueue()
    stopTimeUpdates()
    state.value.error = null
  }

  // Cleanup on unmount
  onUnmounted(() => {
    cleanup()
  })

  return {
    state: readonly(state),
    isQueueEmpty,
    hasAudio,
    progress,
    playAudio,
    queueAudio,
    stopPlayback,
    pausePlayback,
    resumePlayback,
    setVolume,
    seekTo,
    clearQueue,
    skipCurrent,
    setCallbacks,
    testPlayback,
    cleanup
  }
}
