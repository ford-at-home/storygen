import React from 'react'
import { motion } from 'framer-motion'
import { LucideIcon } from 'lucide-react'
import { Button } from './Button'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description: string
  action?: {
    label: string
    onClick: () => void
  }
  secondaryAction?: {
    label: string
    onClick: () => void
  }
  illustration?: 'stories' | 'search' | 'templates' | 'voice'
  className?: string
}

const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  action,
  secondaryAction,
  illustration,
  className,
}) => {
  const renderIllustration = () => {
    if (Icon) {
      return (
        <div className="w-16 h-16 mx-auto mb-6 p-4 bg-gray-100 rounded-full">
          <Icon className="w-8 h-8 text-gray-400" />
        </div>
      )
    }

    if (illustration === 'stories') {
      return (
        <div className="w-24 h-24 mx-auto mb-6 relative">
          <motion.div
            className="absolute inset-0 bg-gradient-to-br from-richmond-river to-richmond-sunset rounded-lg opacity-20"
            animate={{ rotate: [0, 2, -2, 0] }}
            transition={{ duration: 4, repeat: Infinity, ease: "easeInOut" }}
          />
          <motion.div
            className="absolute inset-2 bg-gradient-to-br from-richmond-sunset to-richmond-brick rounded-lg opacity-30"
            animate={{ rotate: [0, -2, 2, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
          />
          <motion.div
            className="absolute inset-4 bg-magnolia-cream rounded-lg border-2 border-gray-200"
            animate={{ y: [0, -2, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          />
        </div>
      )
    }

    if (illustration === 'voice') {
      return (
        <div className="w-24 h-24 mx-auto mb-6 relative flex items-center justify-center">
          <motion.div
            className="w-12 h-12 bg-richmond-river rounded-full flex items-center justify-center"
            animate={{ scale: [1, 1.1, 1] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
          >
            <motion.div
              className="w-4 h-4 bg-white rounded-full"
              animate={{ scale: [1, 0.8, 1] }}
              transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
            />
          </motion.div>
          {[0, 1, 2].map((index) => (
            <motion.div
              key={index}
              className="absolute w-16 h-16 border-2 border-richmond-river/20 rounded-full"
              animate={{ 
                scale: [1, 1.5, 1],
                opacity: [0.3, 0, 0.3]
              }}
              transition={{
                duration: 2,
                repeat: Infinity,
                delay: index * 0.7,
                ease: "easeOut"
              }}
            />
          ))}
        </div>
      )
    }

    if (illustration === 'templates') {
      return (
        <div className="w-24 h-24 mx-auto mb-6 relative">
          {[0, 1, 2].map((index) => (
            <motion.div
              key={index}
              className={`absolute w-16 h-20 bg-gradient-to-br ${
                index === 0 ? 'from-richmond-river to-richmond-sunset' :
                index === 1 ? 'from-richmond-sunset to-richmond-brick' :
                'from-richmond-brick to-moss-green'
              } rounded-lg shadow-sm`}
              style={{
                left: `${index * 8}px`,
                top: `${index * 4}px`,
                zIndex: 3 - index,
              }}
              animate={{ 
                y: [0, -2, 0],
                rotate: [0, 1, 0]
              }}
              transition={{
                duration: 3,
                repeat: Infinity,
                delay: index * 0.5,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>
      )
    }

    // Default search illustration
    return (
      <div className="w-20 h-20 mx-auto mb-6 relative">
        <motion.div
          className="w-12 h-12 border-4 border-gray-300 rounded-full"
          animate={{ rotate: 360 }}
          transition={{ duration: 8, repeat: Infinity, ease: "linear" }}
        />
        <motion.div
          className="absolute top-10 left-10 w-6 h-1 bg-gray-300 rounded-full transform rotate-45"
          animate={{ scale: [1, 1.1, 1] }}
          transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
        />
      </div>
    )
  }

  return (
    <motion.div
      className={cn('text-center py-12 px-4', className)}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5 }}
    >
      <div className="max-w-md mx-auto">
        {renderIllustration()}

        <motion.h3
          className="text-xl font-display font-semibold text-gray-900 mb-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
        >
          {title}
        </motion.h3>

        <motion.p
          className="text-gray-600 mb-6 leading-relaxed"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {description}
        </motion.p>

        {(action || secondaryAction) && (
          <motion.div
            className="flex flex-col sm:flex-row gap-3 justify-center"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            {action && (
              <Button onClick={action.onClick} size="lg">
                {action.label}
              </Button>
            )}
            {secondaryAction && (
              <Button 
                onClick={secondaryAction.onClick} 
                variant="outline" 
                size="lg"
              >
                {secondaryAction.label}
              </Button>
            )}
          </motion.div>
        )}
      </div>
    </motion.div>
  )
}

export default EmptyState