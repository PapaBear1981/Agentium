import { ref, onUnmounted, readonly } from 'vue'
import { arrayBufferToBase64 } from '@/lib/utils'

export interface AudioRecordingState {
  isRecording: boolean
  isInitialized: boolean
  hasPermission: boolean
  audioLevel: number
  error: string | null
}

export interface AudioRecordingOptions {
  sampleRate?: number
  channelCount?: number
  echoCancellation?: boolean
  noiseSuppression?: boolean
  autoGainControl?: boolean
}

export function useAudioRecording(options: AudioRecordingOptions = {}) {
  const state = ref<AudioRecordingState>({
    isRecording: false,
    isInitialized: false,
    hasPermission: false,
    audioLevel: 0,
    error: null
  })

  const defaultOptions = {
    sampleRate: 16000,
    channelCount: 1,
    echoCancellation: true,
    noiseSuppression: true,
    autoGainControl: true,
    ...options
  }

  let mediaRecorder: MediaRecorder | null = null
  let audioChunks: Blob[] = []
  let stream: MediaStream | null = null
  let audioContext: AudioContext | null = null
  let analyser: AnalyserNode | null = null
  let animationFrame: number | null = null

  // Callbacks
  const callbacks = ref<{
    onRecordingStart?: () => void
    onRecordingStop?: () => void
    onRecordingComplete?: (base64Audio: string) => void
    onAudioLevel?: (level: number) => void
    onError?: (error: string) => void
  }>({})

  const initializeAudio = async (): Promise<boolean> => {
    if (state.value.isInitialized) return true

    try {
      state.value.error = null

      // Check if getUserMedia is supported
      if (!navigator.mediaDevices?.getUserMedia) {
        throw new Error('getUserMedia is not supported in this browser')
      }

      // Request microphone access
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: defaultOptions.sampleRate,
          channelCount: defaultOptions.channelCount,
          echoCancellation: defaultOptions.echoCancellation,
          noiseSuppression: defaultOptions.noiseSuppression,
          autoGainControl: defaultOptions.autoGainControl
        }
      })

      // Create audio context for analysis
      audioContext = new AudioContext({ sampleRate: defaultOptions.sampleRate })
      const source = audioContext.createMediaStreamSource(stream)
      analyser = audioContext.createAnalyser()
      analyser.fftSize = 256
      analyser.smoothingTimeConstant = 0.8
      source.connect(analyser)

      // Create MediaRecorder
      const mimeType = getSupportedMimeType()
      mediaRecorder = new MediaRecorder(stream, { mimeType })

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunks.push(event.data)
        }
      }

      mediaRecorder.onstop = () => {
        processRecording()
      }

      mediaRecorder.onerror = (event) => {
        const error = `MediaRecorder error: ${event.error?.message || 'Unknown error'}`
        state.value.error = error
        callbacks.value.onError?.(error)
      }

      state.value.isInitialized = true
      state.value.hasPermission = true

      // Start audio level monitoring
      startAudioLevelMonitoring()

      return true
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Unknown error'
      state.value.error = errorMessage
      state.value.hasPermission = false
      callbacks.value.onError?.(errorMessage)
      return false
    }
  }

  const getSupportedMimeType = (): string => {
    const types = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/mp4',
      'audio/wav'
    ]

    for (const type of types) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type
      }
    }

    return '' // Let MediaRecorder choose default
  }

  const startRecording = (): boolean => {
    if (!state.value.isInitialized || !mediaRecorder) {
      state.value.error = 'Audio not initialized'
      return false
    }

    if (state.value.isRecording) {
      return true
    }

    try {
      audioChunks = []
      mediaRecorder.start()
      state.value.isRecording = true
      state.value.error = null
      callbacks.value.onRecordingStart?.()
      return true
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to start recording'
      state.value.error = errorMessage
      callbacks.value.onError?.(errorMessage)
      return false
    }
  }

  const stopRecording = (): boolean => {
    if (!state.value.isRecording || !mediaRecorder) {
      return false
    }

    try {
      mediaRecorder.stop()
      state.value.isRecording = false
      callbacks.value.onRecordingStop?.()
      return true
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to stop recording'
      state.value.error = errorMessage
      callbacks.value.onError?.(errorMessage)
      return false
    }
  }

  const processRecording = async () => {
    if (audioChunks.length === 0) {
      callbacks.value.onError?.('No audio data recorded')
      return
    }

    try {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' })
      
      // Convert to WAV and encode to base64
      const arrayBuffer = await audioBlob.arrayBuffer()
      const wavBuffer = await convertToWav(arrayBuffer)
      const base64Audio = arrayBufferToBase64(wavBuffer)
      
      callbacks.value.onRecordingComplete?.(base64Audio)
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to process recording'
      state.value.error = errorMessage
      callbacks.value.onError?.(errorMessage)
    }
  }

  const convertToWav = async (webmBuffer: ArrayBuffer): Promise<ArrayBuffer> => {
    if (!audioContext) {
      throw new Error('Audio context not initialized')
    }

    try {
      // Decode the audio data
      const audioBuffer = await audioContext.decodeAudioData(webmBuffer.slice(0))
      return audioBufferToWav(audioBuffer)
    } catch (error) {
      throw new Error(`Failed to convert audio: ${error instanceof Error ? error.message : 'Unknown error'}`)
    }
  }

  const audioBufferToWav = (audioBuffer: AudioBuffer): ArrayBuffer => {
    const length = audioBuffer.length
    const sampleRate = audioBuffer.sampleRate
    const numberOfChannels = 1 // Force mono

    // Get channel data (mix to mono if stereo)
    let channelData: Float32Array
    if (audioBuffer.numberOfChannels === 1) {
      channelData = audioBuffer.getChannelData(0)
    } else {
      // Mix stereo to mono
      const left = audioBuffer.getChannelData(0)
      const right = audioBuffer.getChannelData(1)
      channelData = new Float32Array(length)
      for (let i = 0; i < length; i++) {
        channelData[i] = (left[i] + right[i]) / 2
      }
    }

    // Create WAV file
    const arrayBuffer = new ArrayBuffer(44 + length * 2)
    const view = new DataView(arrayBuffer)

    // WAV header
    const writeString = (offset: number, string: string) => {
      for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i))
      }
    }

    writeString(0, 'RIFF')
    view.setUint32(4, 36 + length * 2, true)
    writeString(8, 'WAVE')
    writeString(12, 'fmt ')
    view.setUint32(16, 16, true)
    view.setUint16(20, 1, true) // PCM
    view.setUint16(22, numberOfChannels, true)
    view.setUint32(24, sampleRate, true)
    view.setUint32(28, sampleRate * numberOfChannels * 2, true)
    view.setUint16(32, numberOfChannels * 2, true)
    view.setUint16(34, 16, true) // 16-bit
    writeString(36, 'data')
    view.setUint32(40, length * 2, true)

    // Convert float samples to 16-bit PCM
    let offset = 44
    for (let i = 0; i < length; i++) {
      const sample = Math.max(-1, Math.min(1, channelData[i]))
      view.setInt16(offset, sample * 0x7FFF, true)
      offset += 2
    }

    return arrayBuffer
  }

  const startAudioLevelMonitoring = () => {
    if (!analyser) return

    const dataArray = new Uint8Array(analyser.frequencyBinCount)

    const updateAudioLevel = () => {
      if (!analyser || !state.value.isInitialized) return

      analyser.getByteFrequencyData(dataArray)
      
      // Calculate RMS (Root Mean Square) for audio level
      let sum = 0
      for (let i = 0; i < dataArray.length; i++) {
        sum += dataArray[i] * dataArray[i]
      }
      const rms = Math.sqrt(sum / dataArray.length)
      const level = rms / 255 // Normalize to 0-1

      state.value.audioLevel = level
      callbacks.value.onAudioLevel?.(level)

      animationFrame = requestAnimationFrame(updateAudioLevel)
    }

    updateAudioLevel()
  }

  const stopAudioLevelMonitoring = () => {
    if (animationFrame) {
      cancelAnimationFrame(animationFrame)
      animationFrame = null
    }
  }

  const cleanup = () => {
    stopRecording()
    stopAudioLevelMonitoring()
    
    if (stream) {
      stream.getTracks().forEach(track => track.stop())
      stream = null
    }
    
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close()
      audioContext = null
    }
    
    mediaRecorder = null
    analyser = null
    audioChunks = []
    
    state.value.isInitialized = false
    state.value.hasPermission = false
    state.value.isRecording = false
    state.value.audioLevel = 0
  }

  const setCallbacks = (newCallbacks: typeof callbacks.value) => {
    callbacks.value = { ...callbacks.value, ...newCallbacks }
  }

  // Cleanup on unmount
  onUnmounted(() => {
    cleanup()
  })

  return {
    state: readonly(state),
    initializeAudio,
    startRecording,
    stopRecording,
    cleanup,
    setCallbacks
  }
}
