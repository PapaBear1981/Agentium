import { ref, computed, watch, onMounted } from 'vue'
import { useAppStore } from '@/stores/app'
import { useAudioRecording } from './useAudioRecording'
import { useVoiceActivityDetection } from './useVoiceActivityDetection'
import { useAudioPlayback } from './useAudioPlayback'
import type { VoiceStateType } from '@/types'

export interface VoiceProcessingOptions {
  enableVAD?: boolean
  vadThreshold?: number
  silenceTimeout?: number
  speechTimeout?: number
  autoPlayTTS?: boolean
  sampleRate?: number
}

export function useVoiceProcessing(options: VoiceProcessingOptions = {}) {
  const store = useAppStore()
  
  const defaultOptions = {
    enableVAD: true,
    vadThreshold: 0.1,
    silenceTimeout: 2000,
    speechTimeout: 500,
    autoPlayTTS: true,
    sampleRate: 16000,
    ...options
  }

  // Initialize audio components
  const audioRecording = useAudioRecording({
    sampleRate: defaultOptions.sampleRate,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true
  })

  const vad = useVoiceActivityDetection(audioRecording, {
    threshold: defaultOptions.vadThreshold,
    silenceTimeout: defaultOptions.silenceTimeout,
    speechTimeout: defaultOptions.speechTimeout,
    minSpeechDuration: 300,
    maxSpeechDuration: 30000
  })

  const audioPlayback = useAudioPlayback({
    autoPlay: defaultOptions.autoPlayTTS,
    volume: 1.0,
    format: 'mp3'
  })

  const isInitialized = ref(false)
  const lastError = ref<string | null>(null)

  // Computed states
  const canRecord = computed(() => 
    isInitialized.value && 
    audioRecording.state.value.hasPermission && 
    !audioPlayback.state.value.isPlaying
  )

  const isRecording = computed(() => audioRecording.state.value.isRecording)
  const isPlaying = computed(() => audioPlayback.state.value.isPlaying)
  const audioLevel = computed(() => audioRecording.state.value.audioLevel)
  const voiceState = computed(() => store.voiceState)

  // Callbacks for external integration
  const callbacks = ref<{
    onVoiceMessage?: (base64Audio: string) => void
    onError?: (error: string) => void
    onStateChange?: (state: VoiceStateType) => void
  }>({})

  const initialize = async (): Promise<boolean> => {
    if (isInitialized.value) return true

    try {
      lastError.value = null
      store.setVoiceState('idle')

      // Test audio playback capability first
      const playbackSupported = await audioPlayback.testPlayback()
      if (!playbackSupported) {
        throw new Error('Audio playback not supported')
      }

      // Initialize audio recording
      const recordingInitialized = await audioRecording.initializeAudio()
      if (!recordingInitialized) {
        throw new Error('Failed to initialize audio recording')
      }

      // Set up audio recording callbacks
      audioRecording.setCallbacks({
        onRecordingStart: () => {
          console.log('Recording started')
          store.setRecording(true)
          store.setVoiceState('listening')
          callbacks.value.onStateChange?.('listening')
        },
        
        onRecordingStop: () => {
          console.log('Recording stopped')
          store.setRecording(false)
          store.setVoiceState('processing')
          callbacks.value.onStateChange?.('processing')
        },
        
        onRecordingComplete: (base64Audio: string) => {
          console.log('Recording complete, sending to server')
          callbacks.value.onVoiceMessage?.(base64Audio)
        },
        
        onAudioLevel: (level: number) => {
          store.setAudioLevel(level)
        },
        
        onError: (error: string) => {
          console.error('Recording error:', error)
          lastError.value = error
          store.setVoiceState('idle')
          store.setRecording(false)
          callbacks.value.onError?.(error)
        }
      })

      // Set up VAD callbacks if enabled
      if (defaultOptions.enableVAD) {
        vad.setCallbacks({
          onSpeechStart: () => {
            console.log('VAD: Speech started')
          },
          
          onSpeechEnd: () => {
            console.log('VAD: Speech ended')
          },
          
          onMaxDurationReached: () => {
            console.log('VAD: Maximum duration reached')
          }
        })
      }

      // Set up audio playback callbacks
      audioPlayback.setCallbacks({
        onPlaybackStart: () => {
          console.log('TTS playback started')
          store.setSpeaking(true)
          store.setVoiceState('speaking')
          callbacks.value.onStateChange?.('speaking')
        },
        
        onPlaybackEnd: () => {
          console.log('TTS playback ended')
          store.setSpeaking(false)
          store.setVoiceState('idle')
          callbacks.value.onStateChange?.('idle')
        },
        
        onPlaybackError: (error: string) => {
          console.error('Playback error:', error)
          lastError.value = error
          store.setSpeaking(false)
          store.setVoiceState('idle')
          callbacks.value.onError?.(error)
        }
      })

      isInitialized.value = true
      console.log('Voice processing initialized successfully')
      return true

    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      lastError.value = errorMessage
      callbacks.value.onError?.(errorMessage)
      return false
    }
  }

  const startListening = async () => {
    if (!canRecord.value) {
      const error = 'Cannot start recording: not initialized or permission denied'
      lastError.value = error
      callbacks.value.onError?.(error)
      return false
    }

    if (defaultOptions.enableVAD) {
      // Use Voice Activity Detection
      vad.start()
      return true
    } else {
      // Manual recording
      return audioRecording.startRecording()
    }
  }

  const stopListening = () => {
    if (defaultOptions.enableVAD) {
      vad.stop()
    } else {
      audioRecording.stopRecording()
    }
  }

  const playTTS = async (base64Audio: string, format: 'mp3' | 'wav' = 'mp3') => {
    try {
      await audioPlayback.playAudio(base64Audio, format)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'TTS playback failed'
      lastError.value = errorMessage
      callbacks.value.onError?.(errorMessage)
    }
  }

  const queueTTS = (base64Audio: string, format: 'mp3' | 'wav' = 'mp3') => {
    audioPlayback.queueAudio(base64Audio, format)
  }

  const stopTTS = () => {
    audioPlayback.stopPlayback()
  }

  const setVolume = (volume: number) => {
    audioPlayback.setVolume(volume)
  }

  const toggleVAD = (enabled: boolean) => {
    defaultOptions.enableVAD = enabled
    if (!enabled && vad.state.value.isListening) {
      vad.stop()
    }
  }

  const updateVADSettings = (settings: {
    threshold?: number
    silenceTimeout?: number
    speechTimeout?: number
  }) => {
    vad.updateOptions(settings)
  }

  const setCallbacks = (newCallbacks: Partial<typeof callbacks.value>) => {
    callbacks.value = { ...callbacks.value, ...newCallbacks }
  }

  // Watch for voice enabled changes
  watch(() => store.voiceEnabled, (enabled) => {
    if (!enabled) {
      stopListening()
      stopTTS()
    }
  })

  // Watch for user settings changes
  watch(() => store.userSettings.autoPlayTTS, (autoPlay) => {
    defaultOptions.autoPlayTTS = autoPlay
  })

  // Auto-initialize on mount
  onMounted(() => {
    if (store.voiceEnabled) {
      initialize()
    }
  })

  return {
    // State
    isInitialized,
    canRecord,
    isRecording,
    isPlaying,
    audioLevel,
    voiceState,
    lastError,
    
    // Audio Recording
    audioRecording: {
      state: audioRecording.state,
      startRecording: audioRecording.startRecording,
      stopRecording: audioRecording.stopRecording
    },
    
    // Voice Activity Detection
    vad: {
      state: vad.state,
      isVoiceDetected: vad.isVoiceDetected,
      forceStart: vad.forceStart,
      forceStop: vad.forceStop
    },
    
    // Audio Playback
    audioPlayback: {
      state: audioPlayback.state,
      progress: audioPlayback.progress,
      setVolume: audioPlayback.setVolume,
      clearQueue: audioPlayback.clearQueue
    },
    
    // Main Methods
    initialize,
    startListening,
    stopListening,
    playTTS,
    queueTTS,
    stopTTS,
    setVolume,
    toggleVAD,
    updateVADSettings,
    setCallbacks
  }
}
