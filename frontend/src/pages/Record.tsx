import React from 'react'
import { motion } from 'framer-motion'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ErrorBoundary } from '@/components/ui'
import { VoiceRecorder } from '@/components/voice'
import { useConversationStore } from '@/stores/conversationStore'
import toast from 'react-hot-toast'

export function Record() {
  const navigate = useNavigate()
  const { startConversation } = useConversationStore()

  const handleTranscription = async (text: string, sessionId?: string) => {
    try {
      if (sessionId) {
        // If we got a session ID from the voice upload, navigate to it
        navigate(`/conversation/${sessionId}`)
      } else {
        // Otherwise start a new conversation with the transcribed text
        const newSessionId = await startConversation(text)
        if (newSessionId) {
          navigate(`/conversation/${newSessionId}`)
        }
      }
    } catch (error) {
      toast.error('Failed to start conversation with voice input')
    }
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gradient-to-br from-magnolia-cream to-dogwood-white">
        <div className="max-w-4xl mx-auto px-4 py-8">
          {/* Header */}
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <Button
              onClick={() => navigate(-1)}
              variant="ghost"
              className="mb-6"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
            
            <div className="text-center">
              <h1 className="text-4xl font-display font-bold text-gray-900 mb-4">
                Tell Your Richmond Story
              </h1>
              <p className="text-xl text-gray-600 max-w-2xl mx-auto">
                Share your thoughts, memories, or ideas about Richmond. I'll help you craft them into a compelling narrative.
              </p>
            </div>
          </motion.div>

          {/* Voice Recorder */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="bg-white rounded-xl shadow-lg p-8 mb-8"
          >
            <VoiceRecorder
              onTranscription={handleTranscription}
              maxDuration={300} // 5 minutes
            />
          </motion.div>

          {/* Tips */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
            className="max-w-2xl mx-auto"
          >
            <h3 className="text-lg font-medium text-gray-900 mb-4 text-center">
              Tips for Great Voice Stories
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white/50 backdrop-blur-sm rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Be Specific</h4>
                <p className="text-sm text-gray-600">
                  Mention specific Richmond locations, experiences, or observations for richer context.
                </p>
              </div>
              <div className="bg-white/50 backdrop-blur-sm rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Speak Naturally</h4>
                <p className="text-sm text-gray-600">
                  Talk as if you're sharing with a friend - natural conversation creates better stories.
                </p>
              </div>
              <div className="bg-white/50 backdrop-blur-sm rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Include Emotions</h4>
                <p className="text-sm text-gray-600">
                  Share how something made you feel or why it matters to you.
                </p>
              </div>
              <div className="bg-white/50 backdrop-blur-sm rounded-lg p-4">
                <h4 className="font-medium text-gray-900 mb-2">Don't Rush</h4>
                <p className="text-sm text-gray-600">
                  Take your time to express your thoughts clearly and completely.
                </p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </ErrorBoundary>
  )
}