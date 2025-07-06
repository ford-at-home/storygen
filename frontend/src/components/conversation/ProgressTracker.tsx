import React from 'react'
import { motion } from 'framer-motion'
import { Check, Circle, Mic, Target, Palette, FileText, Sparkles } from 'lucide-react'
import { ConversationStage } from '@/types'
import { cn } from '@/lib/utils'

interface ProgressTrackerProps {
  currentStage: ConversationStage
  className?: string
  orientation?: 'horizontal' | 'vertical'
}

const stageConfig = {
  [ConversationStage.KICKOFF]: {
    label: 'Voice Input',
    icon: Mic,
    description: 'Share your story idea',
  },
  [ConversationStage.DEPTH_ANALYSIS]: {
    label: 'Deep Dive',
    icon: Target,
    description: 'Explore your story',
  },
  [ConversationStage.ANGLE_SELECTION]: {
    label: 'Find Angle',
    icon: Circle,
    description: 'Choose perspective',
  },
  [ConversationStage.TONE_SELECTION]: {
    label: 'Set Tone',
    icon: Palette,
    description: 'Pick your style',
  },
  [ConversationStage.LENGTH_SELECTION]: {
    label: 'Story Length',
    icon: FileText,
    description: 'Define scope',
  },
  [ConversationStage.READY_TO_GENERATE]: {
    label: 'Generate',
    icon: Sparkles,
    description: 'Create your story',
  },
  [ConversationStage.STORY_GENERATED]: {
    label: 'Complete',
    icon: Check,
    description: 'Story ready',
  },
}

const stageOrder = [
  ConversationStage.KICKOFF,
  ConversationStage.DEPTH_ANALYSIS,
  ConversationStage.ANGLE_SELECTION,
  ConversationStage.TONE_SELECTION,
  ConversationStage.LENGTH_SELECTION,
  ConversationStage.READY_TO_GENERATE,
  ConversationStage.STORY_GENERATED,
]

const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  currentStage,
  className,
  orientation = 'horizontal',
}) => {
  const currentIndex = stageOrder.indexOf(currentStage)

  const getStageStatus = (index: number) => {
    if (index < currentIndex) return 'completed'
    if (index === currentIndex) return 'current'
    return 'upcoming'
  }

  if (orientation === 'vertical') {
    return (
      <div className={cn('space-y-4', className)}>
        {stageOrder.map((stage, index) => {
          const config = stageConfig[stage]
          const status = getStageStatus(index)
          const Icon = config.icon

          return (
            <div key={stage} className="flex items-start space-x-3">
              {/* Icon */}
              <motion.div
                className={cn(
                  'flex items-center justify-center w-8 h-8 rounded-full border-2 transition-colors',
                  status === 'completed' && 'bg-richmond-river border-richmond-river text-white',
                  status === 'current' && 'bg-richmond-sunset border-richmond-sunset text-white',
                  status === 'upcoming' && 'bg-white border-gray-300 text-gray-400'
                )}
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: index * 0.1 }}
              >
                <Icon className="w-4 h-4" />
              </motion.div>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <h4
                  className={cn(
                    'text-sm font-medium',
                    status === 'completed' && 'text-richmond-river',
                    status === 'current' && 'text-richmond-sunset',
                    status === 'upcoming' && 'text-gray-400'
                  )}
                >
                  {config.label}
                </h4>
                <p className="text-xs text-gray-500 mt-1">
                  {config.description}
                </p>
              </div>

              {/* Connection Line */}
              {index < stageOrder.length - 1 && (
                <div
                  className={cn(
                    'absolute left-4 w-0.5 h-6 mt-8 transition-colors',
                    index < currentIndex ? 'bg-richmond-river' : 'bg-gray-200'
                  )}
                />
              )}
            </div>
          )
        })}
      </div>
    )
  }

  return (
    <div className={cn('flex items-center justify-between', className)}>
      {stageOrder.map((stage, index) => {
        const config = stageConfig[stage]
        const status = getStageStatus(index)
        const Icon = config.icon

        return (
          <div key={stage} className="flex flex-col items-center space-y-2">
            {/* Icon */}
            <motion.div
              className={cn(
                'flex items-center justify-center w-10 h-10 rounded-full border-2 transition-all duration-300',
                status === 'completed' && 'bg-richmond-river border-richmond-river text-white',
                status === 'current' && 'bg-richmond-sunset border-richmond-sunset text-white scale-110',
                status === 'upcoming' && 'bg-white border-gray-300 text-gray-400'
              )}
              initial={{ scale: 0 }}
              animate={{ scale: status === 'current' ? 1.1 : 1 }}
              transition={{ delay: index * 0.1, type: "spring", stiffness: 300 }}
            >
              <Icon className="w-5 h-5" />
            </motion.div>

            {/* Label */}
            <div className="text-center">
              <div
                className={cn(
                  'text-xs font-medium',
                  status === 'completed' && 'text-richmond-river',
                  status === 'current' && 'text-richmond-sunset',
                  status === 'upcoming' && 'text-gray-400'
                )}
              >
                {config.label}
              </div>
              <div className="text-xs text-gray-400 hidden sm:block">
                {config.description}
              </div>
            </div>

            {/* Connection Line */}
            {index < stageOrder.length - 1 && (
              <div
                className={cn(
                  'absolute h-0.5 w-8 top-5 transition-colors duration-300',
                  index < currentIndex ? 'bg-richmond-river' : 'bg-gray-200'
                )}
                style={{ left: `${index * 14.28 + 7.14}%` }}
              />
            )}
          </div>
        )
      })}
    </div>
  )
}

export default ProgressTracker