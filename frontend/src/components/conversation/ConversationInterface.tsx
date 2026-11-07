import React, { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Send, Mic } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useConversationStore } from '@/stores/conversationStore'
import ConversationBubble from './ConversationBubble'
import TypingIndicator from './TypingIndicator'
import ProgressTracker from './ProgressTracker'
import VoiceRecorder from '../voice/VoiceRecorder'
import { cn } from '@/lib/utils'

interface ConversationInterfaceProps {
  className?: string
  sessionId?: string
  showProgress?: boolean
}

const ConversationInterface: React.FC<ConversationInterfaceProps> = ({
  className,
  sessionId,
  showProgress = true,
}) => {
  const {
    session,
    isLoading,
    error,
    continueConversation,
    selectOption,
    loadSession,
  } = useConversationStore()

  const [inputValue, setInputValue] = useState('')
  const [showVoiceRecorder, setShowVoiceRecorder] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  // Load session on mount
  useEffect(() => {
    if (sessionId && sessionId !== session?.session_id) {
      loadSession(sessionId)
    }
  }, [sessionId, session?.session_id, loadSession])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [session?.conversation_history, isLoading])

  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return

    const message = inputValue.trim()
    setInputValue('')
    
    await continueConversation(message)
    inputRef.current?.focus()
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const handleOptionSelect = async (optionType: string, index: number) => {
    await selectOption(optionType, index)
  }

  const handleVoiceTranscription = async (text: string) => {
    setShowVoiceRecorder(false)
    setInputValue(text)
    // Auto-send transcription
    await continueConversation(text)
  }

  const getLatestOptions = () => {
    if (!session?.conversation_history) return null
    
    const lastMessage = session.conversation_history[session.conversation_history.length - 1]
    return lastMessage?.metadata?.options || null
  }

  const options = getLatestOptions()

  return (
    <div className={cn('flex flex-col h-full max-w-4xl mx-auto', className)}>
      {/* Progress Tracker */}
      {showProgress && session && (
        <motion.div
          className="p-4 bg-white border-b border-gray-200"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <ProgressTracker
            currentStage={session.current_stage}
            orientation="horizontal"
          />
        </motion.div>
      )}

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Welcome Message */}
        {!session?.conversation_history?.length && (
          <motion.div
            className="text-center py-8"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-2xl font-display text-gray-900 mb-2">
              Let's Create Your Richmond Story
            </h2>
            <p className="text-gray-600 max-w-md mx-auto">
              Share your idea using voice or text, and I'll help you craft a compelling narrative rooted in Richmond's unique character.
            </p>
          </motion.div>
        )}

        {/* Conversation History */}
        <AnimatePresence>
          {session?.conversation_history?.map((turn, index) => (
            <ConversationBubble
              key={index}
              turn={turn}
              showTimestamp={index === session.conversation_history.length - 1}
            />
          ))}
        </AnimatePresence>

        {/* Typing Indicator */}
        <AnimatePresence>
          {isLoading && <TypingIndicator />}
        </AnimatePresence>

        {/* Option Buttons */}
        <AnimatePresence>
          {options && !isLoading && (
            <motion.div
              className="space-y-4"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.3 }}
            >
              {Object.entries(options).map(([optionType, optionList]) => (
                <div key={optionType} className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700 capitalize">
                    Choose {optionType.replace('_', ' ')}:
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {(optionList as string[]).map((option, index) => (
                      <Button
                        key={index}
                        onClick={() => handleOptionSelect(optionType, index)}
                        variant="outline"
                        className="text-left justify-start h-auto p-3 whitespace-normal"
                      >
                        {option}
                      </Button>
                    ))}
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Error Message */}
        <AnimatePresence>
          {error && (
            <motion.div
              className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700"
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              transition={{ duration: 0.2 }}
            >
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        <div ref={messagesEndRef} />
      </div>

      {/* Voice Recorder */}
      <AnimatePresence>
        {showVoiceRecorder && (
          <motion.div
            className="p-4 bg-magnolia-cream border-t border-gray-200"
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3 }}
          >
            <VoiceRecorder
              onTranscription={handleVoiceTranscription}
              maxDuration={180} // 3 minutes for conversation
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Input Area */}
      {!options && !showVoiceRecorder && (
        <motion.div
          className="p-4 bg-white border-t border-gray-200"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3 }}
        >
          <div className="flex items-end space-x-2">
            <div className="flex-1">
              <Input
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Share your story idea..."
                disabled={isLoading}
                className="resize-none"
              />
            </div>
            
            <Button
              onClick={() => setShowVoiceRecorder(!showVoiceRecorder)}
              variant="outline"
              size="md"
              className="p-3"
              disabled={isLoading}
            >
              <Mic className="w-4 h-4" />
            </Button>
            
            <Button
              onClick={handleSendMessage}
              disabled={!inputValue.trim() || isLoading}
              size="md"
              className="p-3"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
        </motion.div>
      )}
    </div>
  )
}

export default ConversationInterface