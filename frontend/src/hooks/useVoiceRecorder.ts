import { useState, useRef, useCallback } from 'react'

export interface VoiceRecorderState {
  isRecording: boolean
  isPlaying: boolean
  isProcessing: boolean
  duration: number
  audioBlob: Blob | null
  audioUrl: string | null
  error: string | null
}

export const useVoiceRecorder = () => {
  const [state, setState] = useState<VoiceRecorderState>({
    isRecording: false,
    isPlaying: false,
    isProcessing: false,
    duration: 0,
    audioBlob: null,
    audioUrl: null,
    error: null,
  })

  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const analyserRef = useRef<AnalyserNode | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const timerRef = useRef<NodeJS.Timeout | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const startRecording = useCallback(async () => {
    try {
      setState(prev => ({ ...prev, error: null, isProcessing: true }))

      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      streamRef.current = stream

      // Create audio context for visualization
      audioContextRef.current = new AudioContext()
      analyserRef.current = audioContextRef.current.createAnalyser()
      const source = audioContextRef.current.createMediaStreamSource(stream)
      source.connect(analyserRef.current)
      analyserRef.current.fftSize = 256

      // Create media recorder
      mediaRecorderRef.current = new MediaRecorder(stream)
      chunksRef.current = []

      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data)
        }
      }

      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(chunksRef.current, { type: 'audio/wav' })
        const audioUrl = URL.createObjectURL(audioBlob)
        
        setState(prev => ({
          ...prev,
          audioBlob,
          audioUrl,
          isRecording: false,
          isProcessing: false,
        }))
      }

      mediaRecorderRef.current.start()

      // Start timer
      timerRef.current = setInterval(() => {
        setState(prev => ({ ...prev, duration: prev.duration + 1 }))
      }, 1000)

      setState(prev => ({
        ...prev,
        isRecording: true,
        isProcessing: false,
        duration: 0,
      }))
    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Failed to start recording. Please check microphone permissions.',
        isProcessing: false,
      }))
    }
  }, [])

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && state.isRecording) {
      mediaRecorderRef.current.stop()
      
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
      
      if (timerRef.current) {
        clearInterval(timerRef.current)
      }
      
      if (audioContextRef.current) {
        audioContextRef.current.close()
      }
    }
  }, [state.isRecording])

  const reset = useCallback(() => {
    stopRecording()
    
    if (state.audioUrl) {
      URL.revokeObjectURL(state.audioUrl)
    }
    
    setState({
      isRecording: false,
      isPlaying: false,
      isProcessing: false,
      duration: 0,
      audioBlob: null,
      audioUrl: null,
      error: null,
    })
  }, [state.audioUrl, stopRecording])

  const getFrequencyData = useCallback(() => {
    if (!analyserRef.current) return new Uint8Array(0)
    
    const bufferLength = analyserRef.current.frequencyBinCount
    const dataArray = new Uint8Array(bufferLength)
    analyserRef.current.getByteFrequencyData(dataArray)
    return dataArray
  }, [])

  return {
    ...state,
    startRecording,
    stopRecording,
    reset,
    getFrequencyData,
  }
}