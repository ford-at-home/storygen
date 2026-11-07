import React from 'react'
import { motion } from 'framer-motion'
import { cn } from '@/lib/utils'

interface TypingIndicatorProps {
  className?: string
}

const TypingIndicator: React.FC<TypingIndicatorProps> = ({ className }) => {
  return (
    <motion.div
      className={cn('flex justify-start mb-4', className)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ duration: 0.3 }}
    >
      <div className="bg-white border border-gray-200 shadow-sm px-4 py-3 rounded-2xl relative max-w-20">
        <div className="flex space-x-1">
          {[0, 1, 2].map((index) => (
            <motion.div
              key={index}
              className="w-2 h-2 bg-gray-400 rounded-full"
              animate={{ 
                y: [0, -8, 0],
                opacity: [0.4, 1, 0.4]
              }}
              transition={{
                duration: 1.4,
                repeat: Infinity,
                delay: index * 0.2,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>

        {/* Speech Bubble Tail */}
        <div className="absolute top-3 w-3 h-3 bg-white border-l border-b border-gray-200 transform rotate-45 -left-1" />
      </div>
    </motion.div>
  )
}

export default TypingIndicator