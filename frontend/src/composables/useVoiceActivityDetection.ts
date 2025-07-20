import { ref, computed, onUnmounted, readonly } from 'vue'
import type { useAudioRecording } from './useAudioRecording'

export interface VADOptions {
  threshold: number
  silenceTimeout: number
  speechTimeout: number
  minSpeechDuration: number
  maxSpeechDuration: number
}

export interface VADState {
  isListening: boolean
  isActive: boolean
  speechDetected: boolean
  silenceDuration: number
  speechDuration: number
}

export function useVoiceActivityDetection(
  audioRecording: ReturnType<typeof useAudioRecording>,
  options: Partial<VADOptions> = {}
) {
  const defaultOptions: VADOptions = {
    threshold: 0.1,
    silenceTimeout: 2000,
    speechTimeout: 500,
    minSpeechDuration: 300,
    maxSpeechDuration: 30000,
    ...options
  }

  const state = ref<VADState>({
    isListening: false,
    isActive: false,
    speechDetected: false,
    silenceDuration: 0,
    speechDuration: 0
  })

  const callbacks = ref<{
    onSpeechStart?: () => void
    onSpeechEnd?: () => void
    onSilenceStart?: () => void
    onSilenceEnd?: () => void
    onMaxDurationReached?: () => void
  }>({})

  let silenceTimer: number | null = null
  let speechTimer: number | null = null
  let maxDurationTimer: number | null = null
  let lastAudioLevel = 0
  let speechStartTime = 0
  let silenceStartTime = 0

  const isVoiceDetected = computed(() => {
    return audioRecording.state.value.audioLevel > defaultOptions.threshold
  })

  const start = () => {
    if (state.value.isListening) return

    state.value.isListening = true
    state.value.isActive = false
    state.value.speechDetected = false
    state.value.silenceDuration = 0
    state.value.speechDuration = 0

    // Set up audio level monitoring
    audioRecording.setCallbacks({
      ...audioRecording.setCallbacks,
      onAudioLevel: handleAudioLevel
    })

    console.log('Voice Activity Detection started')
  }

  const stop = () => {
    if (!state.value.isListening) return

    state.value.isListening = false
    state.value.isActive = false
    state.value.speechDetected = false

    clearAllTimers()
    
    // Stop recording if active
    if (audioRecording.state.value.isRecording) {
      audioRecording.stopRecording()
    }

    console.log('Voice Activity Detection stopped')
  }

  const handleAudioLevel = (level: number) => {
    if (!state.value.isListening) return

    lastAudioLevel = level
    const voiceDetected = level > defaultOptions.threshold

    if (voiceDetected) {
      handleVoiceDetected()
    } else {
      handleSilenceDetected()
    }
  }

  const handleVoiceDetected = () => {
    // Clear silence timer if running
    if (silenceTimer) {
      window.clearTimeout(silenceTimer)
      silenceTimer = null
      state.value.silenceDuration = 0
    }

    if (!state.value.speechDetected) {
      // Speech just started
      if (!speechTimer) {
        speechTimer = window.setTimeout(() => {
          if (state.value.isListening && lastAudioLevel > defaultOptions.threshold) {
            startSpeechRecording()
          }
          speechTimer = null
        }, defaultOptions.speechTimeout)
      }
    } else {
      // Continue speech
      updateSpeechDuration()
    }
  }

  const handleSilenceDetected = () => {
    // Clear speech timer if running
    if (speechTimer) {
      window.clearTimeout(speechTimer)
      speechTimer = null
    }

    if (state.value.speechDetected) {
      // Silence detected during speech
      if (!silenceTimer) {
        silenceStartTime = Date.now()
        silenceTimer = window.setTimeout(() => {
          if (state.value.isListening && state.value.speechDetected) {
            endSpeechRecording()
          }
          silenceTimer = null
        }, defaultOptions.silenceTimeout)
      } else {
        // Update silence duration
        state.value.silenceDuration = Date.now() - silenceStartTime
      }
    }
  }

  const startSpeechRecording = () => {
    if (!state.value.isListening || state.value.speechDetected) return

    console.log('Speech detected - starting recording')
    
    state.value.speechDetected = true
    state.value.isActive = true
    speechStartTime = Date.now()
    
    // Start recording
    const started = audioRecording.startRecording()
    if (started) {
      callbacks.value.onSpeechStart?.()
      
      // Set maximum duration timer
      maxDurationTimer = window.setTimeout(() => {
        console.log('Maximum speech duration reached')
        callbacks.value.onMaxDurationReached?.()
        endSpeechRecording()
      }, defaultOptions.maxSpeechDuration)
    } else {
      // Failed to start recording
      state.value.speechDetected = false
      state.value.isActive = false
    }
  }

  const endSpeechRecording = () => {
    if (!state.value.speechDetected) return

    const speechDuration = Date.now() - speechStartTime
    
    console.log(`Speech ended - duration: ${speechDuration}ms`)
    
    // Check minimum duration
    if (speechDuration < defaultOptions.minSpeechDuration) {
      console.log('Speech too short, discarding')
      audioRecording.stopRecording()
      resetState()
      return
    }

    state.value.speechDetected = false
    state.value.isActive = false
    state.value.speechDuration = speechDuration

    // Stop recording
    audioRecording.stopRecording()
    callbacks.value.onSpeechEnd?.()
    
    clearAllTimers()
  }

  const updateSpeechDuration = () => {
    if (state.value.speechDetected && speechStartTime > 0) {
      state.value.speechDuration = Date.now() - speechStartTime
    }
  }

  const resetState = () => {
    state.value.speechDetected = false
    state.value.isActive = false
    state.value.silenceDuration = 0
    state.value.speechDuration = 0
    speechStartTime = 0
    silenceStartTime = 0
    clearAllTimers()
  }

  const clearAllTimers = () => {
    if (silenceTimer) {
      window.clearTimeout(silenceTimer)
      silenceTimer = null
    }
    
    if (speechTimer) {
      window.clearTimeout(speechTimer)
      speechTimer = null
    }
    
    if (maxDurationTimer) {
      window.clearTimeout(maxDurationTimer)
      maxDurationTimer = null
    }
  }

  const setCallbacks = (newCallbacks: Partial<typeof callbacks.value>) => {
    callbacks.value = { ...callbacks.value, ...newCallbacks }
  }

  const updateOptions = (newOptions: Partial<VADOptions>) => {
    Object.assign(defaultOptions, newOptions)
  }

  // Manual controls
  const forceStart = () => {
    if (!state.value.isListening) return
    startSpeechRecording()
  }

  const forceStop = () => {
    if (!state.value.speechDetected) return
    endSpeechRecording()
  }

  // Cleanup on unmount
  onUnmounted(() => {
    stop()
  })

  return {
    state: readonly(state),
    isVoiceDetected,
    start,
    stop,
    forceStart,
    forceStop,
    setCallbacks,
    updateOptions,
    resetState
  }
}
