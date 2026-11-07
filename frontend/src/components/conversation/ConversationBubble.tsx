import React from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import { ConversationTurn } from '@/types'
import { cn } from '@/lib/utils'

interface ConversationBubbleProps {
  turn: ConversationTurn
  showTimestamp?: boolean
  className?: string
}

const ConversationBubble: React.FC<ConversationBubbleProps> = ({
  turn,
  showTimestamp = false,
  className,
}) => {
  const isUser = turn.role === 'user'
  const isSystem = turn.role === 'system'

  return (
    <motion.div
      className={cn(
        'flex w-full mb-4',
        isUser ? 'justify-end' : 'justify-start',
        className
      )}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div
        className={cn(
          'max-w-xs lg:max-w-md px-4 py-3 rounded-2xl relative',
          isUser && 'bg-richmond-river text-white',
          !isUser && !isSystem && 'bg-white border border-gray-200 text-gray-900 shadow-sm',
          isSystem && 'bg-magnolia-cream text-gray-700 text-sm italic border border-gray-100'
        )}
      >
        {/* Message Content */}
        <div className="whitespace-pre-wrap leading-relaxed">
          {turn.content}
        </div>

        {/* Timestamp */}
        {showTimestamp && (
          <div
            className={cn(
              'text-xs mt-2 opacity-70',
              isUser ? 'text-white/80' : 'text-gray-500'
            )}
          >
            {format(new Date(turn.timestamp), 'HH:mm')}
          </div>
        )}

        {/* Options */}
        {turn.metadata?.options && (
          <div className="mt-3 space-y-2">
            {Object.entries(turn.metadata.options).map(([key, options]) => (
              <div key={key} className="space-y-1">
                <div className="text-xs font-medium opacity-80 capitalize">
                  {key.replace('_', ' ')}:
                </div>
                <div className="space-y-1">
                  {(options as string[]).map((option, index) => (
                    <button
                      key={index}
                      className={cn(
                        'block w-full text-left px-3 py-2 rounded-lg text-sm transition-colors',
                        'bg-white/10 hover:bg-white/20 border border-white/20',
                        'focus:outline-none focus:ring-2 focus:ring-white/50'
                      )}
                    >
                      {option}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Speech Bubble Tail */}
        <div
          className={cn(
            'absolute top-3 w-3 h-3 transform rotate-45',
            isUser && 'bg-richmond-river -right-1',
            !isUser && !isSystem && 'bg-white border-l border-b border-gray-200 -left-1',
            isSystem && 'bg-magnolia-cream border-l border-b border-gray-100 -left-1'
          )}
        />
      </div>
    </motion.div>
  )
}

export default ConversationBubble