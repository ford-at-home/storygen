import React from 'react'
import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'
import { Spinner } from './Spinner'
import { cn } from '@/lib/utils'

interface LoadingStateProps {
  title?: string
  description?: string
  size?: 'sm' | 'md' | 'lg'
  variant?: 'spinner' | 'skeleton' | 'dots' | 'richmond'
  className?: string
}

const LoadingState: React.FC<LoadingStateProps> = ({
  title = 'Loading...',
  description,
  size = 'md',
  variant = 'spinner',
  className,
}) => {
  const sizeClasses = {
    sm: 'py-8',
    md: 'py-12',
    lg: 'py-16',
  }

  if (variant === 'skeleton') {
    return (
      <div className={cn('space-y-4', sizeClasses[size], className)}>
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-3/4"></div>
          <div className="space-y-2">
            <div className="h-4 bg-gray-200 rounded"></div>
            <div className="h-4 bg-gray-200 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    )
  }

  if (variant === 'dots') {
    return (
      <div className={cn('flex items-center justify-center', sizeClasses[size], className)}>
        <div className="flex space-x-2">
          {[0, 1, 2].map((index) => (
            <motion.div
              key={index}
              className="w-3 h-3 bg-richmond-river rounded-full"
              animate={{
                y: [0, -12, 0],
                opacity: [0.4, 1, 0.4],
              }}
              transition={{
                duration: 1.2,
                repeat: Infinity,
                delay: index * 0.2,
                ease: "easeInOut"
              }}
            />
          ))}
        </div>
      </div>
    )
  }

  if (variant === 'richmond') {
    return (
      <div className={cn('flex flex-col items-center justify-center text-center', sizeClasses[size], className)}>
        <motion.div
          className="relative mb-6"
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          {/* Richmond-inspired loading animation */}
          <motion.div
            className="w-16 h-16 border-4 border-richmond-river/20 rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="absolute inset-2 border-4 border-richmond-sunset/40 rounded-full border-t-transparent"
            animate={{ rotate: -360 }}
            transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
          />
          <motion.div
            className="absolute inset-4 w-8 h-8 bg-richmond-brick/20 rounded-full"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, ease: "easeInOut" }}
          />
        </motion.div>

        <motion.h3
          className="text-lg font-display font-medium text-gray-900 mb-2"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
        >
          {title}
        </motion.h3>

        {description && (
          <motion.p
            className="text-gray-600 max-w-sm"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            {description}
          </motion.p>
        )}

        <motion.div
          className="mt-4 flex space-x-1"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.4 }}
        >
          {['Richmond', 'stories', 'coming', 'to', 'life'].map((word, index) => (
            <motion.span
              key={word}
              className="text-xs text-gray-400"
              animate={{ opacity: [0.4, 1, 0.4] }}
              transition={{
                duration: 2,
                repeat: Infinity,
                delay: index * 0.3,
                ease: "easeInOut"
              }}
            >
              {word}
            </motion.span>
          ))}
        </motion.div>
      </div>
    )
  }

  return (
    <div className={cn('flex flex-col items-center justify-center text-center', sizeClasses[size], className)}>
      <motion.div
        initial={{ opacity: 0, scale: 0.8 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.3 }}
      >
        <Spinner 
          size={size === 'sm' ? 'sm' : size === 'lg' ? 'lg' : 'md'} 
          className="mb-4" 
        />
      </motion.div>

      <motion.h3
        className="text-lg font-medium text-gray-900 mb-2"
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
      >
        {title}
      </motion.h3>

      {description && (
        <motion.p
          className="text-gray-600 max-w-sm"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          {description}
        </motion.p>
      )}
    </div>
  )
}

export default LoadingState