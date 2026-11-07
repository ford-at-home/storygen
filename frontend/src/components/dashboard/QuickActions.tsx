import React from 'react'
import { motion } from 'framer-motion'
import { 
  Mic, 
  FileText, 
  Template, 
  Sparkles, 
  Share2, 
  Download,
  Plus,
  Zap
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { cn } from '@/lib/utils'

interface QuickActionsProps {
  onStartVoiceStory?: () => void
  onStartTextStory?: () => void
  onBrowseTemplates?: () => void
  onEnhanceStory?: () => void
  onShareStory?: () => void
  onExportStory?: () => void
  className?: string
}

const QuickActions: React.FC<QuickActionsProps> = ({
  onStartVoiceStory,
  onStartTextStory,
  onBrowseTemplates,
  onEnhanceStory,
  onShareStory,
  onExportStory,
  className,
}) => {
  const primaryActions = [
    {
      icon: Mic,
      title: 'Voice Story',
      description: 'Start with voice recording',
      color: 'from-richmond-river to-richmond-sunset',
      onClick: onStartVoiceStory,
      featured: true,
    },
    {
      icon: FileText,
      title: 'Text Story',
      description: 'Begin with conversation',
      color: 'from-richmond-sunset to-richmond-brick',
      onClick: onStartTextStory,
      featured: true,
    },
    {
      icon: Template,
      title: 'Use Template',
      description: 'Start with a structure',
      color: 'from-moss-green to-richmond-river',
      onClick: onBrowseTemplates,
      featured: true,
    },
  ]

  const secondaryActions = [
    {
      icon: Sparkles,
      title: 'Enhance',
      description: 'Improve existing story',
      onClick: onEnhanceStory,
    },
    {
      icon: Share2,
      title: 'Share',
      description: 'Share your latest story',
      onClick: onShareStory,
    },
    {
      icon: Download,
      title: 'Export',
      description: 'Download as PDF',
      onClick: onExportStory,
    },
  ]

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div>
        <h2 className="text-2xl font-display font-bold text-gray-900">
          Quick Actions
        </h2>
        <p className="text-gray-600 mt-1">
          Jump right into creating your next Richmond story
        </p>
      </div>

      {/* Primary Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {primaryActions.map((action, index) => (
          <motion.div
            key={action.title}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: index * 0.1 }}
            whileHover={{ y: -2 }}
            whileTap={{ scale: 0.98 }}
          >
            <Card className="overflow-hidden hover:shadow-lg transition-all duration-200 cursor-pointer group">
              <div className={`h-24 bg-gradient-to-br ${action.color} relative`}>
                <div className="absolute inset-0 bg-black/10 group-hover:bg-black/5 transition-colors" />
                <div className="absolute top-4 left-4">
                  <div className="p-2 bg-white/20 rounded-lg backdrop-blur-sm">
                    <action.icon className="w-6 h-6 text-white" />
                  </div>
                </div>
                <div className="absolute bottom-4 right-4">
                  <Plus className="w-5 h-5 text-white/60 group-hover:text-white/80 transition-colors" />
                </div>
              </div>
              <CardContent className="p-4" onClick={action.onClick}>
                <h3 className="font-medium text-gray-900 mb-1">
                  {action.title}
                </h3>
                <p className="text-sm text-gray-600">
                  {action.description}
                </p>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>

      {/* Secondary Actions */}
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-4">
          Story Management
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {secondaryActions.map((action, index) => (
            <motion.div
              key={action.title}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.3, delay: 0.3 + index * 0.1 }}
            >
              <Button
                onClick={action.onClick}
                variant="outline"
                className="w-full h-auto p-4 flex flex-col items-center space-y-2 hover:bg-gray-50"
              >
                <action.icon className="w-5 h-5 text-gray-600" />
                <div className="text-center">
                  <div className="font-medium text-sm">{action.title}</div>
                  <div className="text-xs text-gray-500">{action.description}</div>
                </div>
              </Button>
            </motion.div>
          ))}
        </div>
      </div>

      {/* Featured Tip */}
      <motion.div
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5, delay: 0.6 }}
      >
        <Card className="bg-gradient-to-r from-magnolia-cream to-dogwood-white border-richmond-sunset/20">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <div className="p-2 bg-richmond-sunset/20 rounded-lg">
                <Zap className="w-5 h-5 text-richmond-sunset" />
              </div>
              <div>
                <h4 className="font-medium text-gray-900 mb-1">
                  Pro Tip: Voice Stories
                </h4>
                <p className="text-sm text-gray-600">
                  Voice recordings create more natural, conversational stories. Try speaking about a Richmond memory or observation for the best results.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  )
}

export default QuickActions