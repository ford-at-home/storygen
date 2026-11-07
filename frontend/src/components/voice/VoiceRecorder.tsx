import React, { useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Mic, MicOff, Play, Pause, RotateCcw, Upload } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Progress } from '@/components/ui/Progress'
import { Spinner } from '@/components/ui/Spinner'
import { useVoiceRecorder } from '@/hooks/useVoiceRecorder'
import { storyAPI } from '@/services/storyAPI'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

interface VoiceRecorderProps {
  onTranscription?: (text: string, sessionId?: string) => void
  className?: string
  maxDuration?: number // in seconds
}

const VoiceRecorder: React.FC<VoiceRecorderProps> = ({
  onTranscription,
  className,
  maxDuration = 300, // 5 minutes default
}) => {
  const {
    isRecording,
    isPlaying,
    isProcessing,
    duration,
    audioBlob,
    audioUrl,
    error,
    startRecording,
    stopRecording,
    reset,
    getFrequencyData,
  } = useVoiceRecorder()

  const canvasRef = useRef<HTMLCanvasElement>(null)
  const audioRef = useRef<HTMLAudioElement>(null)
  const animationFrameRef = useRef<number>()

  // Waveform visualization
  useEffect(() => {
    if (!isRecording || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const draw = () => {
      const frequencyData = getFrequencyData()
      const width = canvas.width
      const height = canvas.height

      ctx.clearRect(0, 0, width, height)
      
      // Set gradient
      const gradient = ctx.createLinearGradient(0, 0, width, 0)
      gradient.addColorStop(0, '#1e3a5f')
      gradient.addColorStop(0.5, '#f4a261')
      gradient.addColorStop(1, '#e76f51')
      
      ctx.fillStyle = gradient

      const barWidth = width / frequencyData.length
      
      for (let i = 0; i < frequencyData.length; i++) {
        const barHeight = (frequencyData[i] / 255) * height * 0.8
        const x = i * barWidth
        const y = (height - barHeight) / 2
        
        ctx.fillRect(x, y, barWidth - 1, barHeight)
      }

      animationFrameRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      if (animationFrameRef.current) {
        cancelAnimationFrame(animationFrameRef.current)
      }
    }
  }, [isRecording, getFrequencyData])

  // Auto-stop recording at max duration
  useEffect(() => {
    if (isRecording && duration >= maxDuration) {
      stopRecording()
      toast.warning(`Maximum recording duration of ${maxDuration / 60} minutes reached`)
    }
  }, [duration, maxDuration, isRecording, stopRecording])

  const handlePlayPause = () => {
    if (!audioRef.current || !audioUrl) return

    if (isPlaying) {
      audioRef.current.pause()
    } else {
      audioRef.current.play()
    }
  }

  const handleUpload = async () => {
    if (!audioBlob) return

    try {
      const { transcription, sessionId } = await storyAPI.uploadAudio(audioBlob)
      onTranscription?.(transcription, sessionId)
      toast.success('Audio processed successfully!')
    } catch (error) {
      toast.error('Failed to process audio')
    }
  }

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const recordingProgress = Math.min((duration / maxDuration) * 100, 100)

  return (
    <div className={cn('w-full max-w-md mx-auto p-6 space-y-6', className)}>
      {/* Recording Button */}
      <div className="flex flex-col items-center space-y-4">
        <motion.div
          className="relative"
          whileTap={{ scale: 0.95 }}
        >
          <Button
            onClick={isRecording ? stopRecording : startRecording}
            disabled={isProcessing}
            size="xl"
            variant={isRecording ? 'destructive' : 'primary'}
            className={cn(
              'rounded-full w-20 h-20 transition-all duration-300',
              isRecording && 'animate-pulse-slow'
            )}
          >
            {isProcessing ? (
              <Spinner size="lg" />
            ) : isRecording ? (
              <MicOff className="w-8 h-8" />
            ) : (
              <Mic className="w-8 h-8" />
            )}
          </Button>
          
          {/* Pulse animation rings */}
          <AnimatePresence>
            {isRecording && (
              <>
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-richmond-brick"
                  initial={{ scale: 1, opacity: 1 }}
                  animate={{ scale: 1.5, opacity: 0 }}
                  exit={{ scale: 1, opacity: 0 }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeOut"
                  }}
                />
                <motion.div
                  className="absolute inset-0 rounded-full border-2 border-richmond-brick"
                  initial={{ scale: 1, opacity: 1 }}
                  animate={{ scale: 2, opacity: 0 }}
                  exit={{ scale: 1, opacity: 0 }}
                  transition={{
                    duration: 2,
                    repeat: Infinity,
                    ease: "easeOut",
                    delay: 0.5
                  }}
                />
              </>
            )}
          </AnimatePresence>
        </motion.div>

        {/* Status Text */}
        <motion.p
          className="text-sm font-medium text-gray-600"
          key={isRecording ? 'recording' : 'ready'}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
        >
          {isProcessing
            ? 'Initializing...'
            : isRecording
            ? 'Recording... Tap to stop'
            : audioBlob
            ? 'Recording complete'
            : 'Tap to start recording'
          }
        </motion.p>
      </div>

      {/* Timer and Progress */}
      <AnimatePresence>
        {(isRecording || audioBlob) && (
          <motion.div
            className="space-y-3"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span className="font-mono font-medium">{formatDuration(duration)}</span>
              <span className="text-xs">
                Max: {formatDuration(maxDuration)}
              </span>
            </div>
            
            {isRecording && (
              <Progress
                value={recordingProgress}
                className="h-2"
                indicatorClassName={
                  recordingProgress > 90 ? 'bg-richmond-brick' : undefined
                }
              />
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Waveform Visualization */}
      <AnimatePresence>
        {isRecording && (
          <motion.div
            className="w-full h-20 bg-gray-50 rounded-lg overflow-hidden"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.3 }}
          >
            <canvas
              ref={canvasRef}
              width={300}
              height={80}
              className="w-full h-full"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Playback Controls */}
      <AnimatePresence>
        {audioBlob && !isRecording && (
          <motion.div
            className="flex items-center justify-center space-x-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            transition={{ duration: 0.3 }}
          >
            <Button
              onClick={handlePlayPause}
              variant="outline"
              size="md"
              className="w-12 h-12 rounded-full p-0"
            >
              {isPlaying ? (
                <Pause className="w-4 h-4" />
              ) : (
                <Play className="w-4 h-4 ml-0.5" />
              )}
            </Button>

            <Button
              onClick={handleUpload}
              variant="primary"
              className="flex items-center space-x-2"
            >
              <Upload className="w-4 h-4" />
              <span>Process Audio</span>
            </Button>

            <Button
              onClick={reset}
              variant="ghost"
              size="md"
              className="w-12 h-12 rounded-full p-0"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Hidden Audio Element */}
      {audioUrl && (
        <audio
          ref={audioRef}
          src={audioUrl}
          onPlay={() => {
            // setState for isPlaying would go here if we had access to it
          }}
          onPause={() => {
            // setState for isPlaying would go here if we had access to it
          }}
          onEnded={() => {
            // setState for isPlaying would go here if we had access to it
          }}
        />
      )}

      {/* Error Message */}
      <AnimatePresence>
        {error && (
          <motion.div
            className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            transition={{ duration: 0.2 }}
          >
            {error}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default VoiceRecorder