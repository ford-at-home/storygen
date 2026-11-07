import React from 'react'
import { motion } from 'framer-motion'
import { Eye, Play, BookOpen, Clock, Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Template } from '@/types'
import { cn } from '@/lib/utils'

interface TemplateCardProps {
  template: Template
  onSelect?: (template: Template) => void
  onPreview?: (template: Template) => void
  className?: string
}

const TemplateCard: React.FC<TemplateCardProps> = ({
  template,
  onSelect,
  onPreview,
  className,
}) => {
  const totalWordCount = template.structure.sections.reduce(
    (total, section) => total + section.word_count_guide, 
    0
  )

  const readingTime = Math.ceil(totalWordCount / 200)

  return (
    <motion.div
      className={cn('group', className)}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -2 }}
    >
      <Card className="h-full hover:shadow-lg transition-all duration-200">
        {/* Header with gradient */}
        <div className="h-24 bg-gradient-to-br from-richmond-river via-richmond-sunset to-richmond-brick rounded-t-lg relative overflow-hidden">
          <div className="absolute inset-0 bg-black/10" />
          <div className="absolute bottom-2 right-2">
            <Button
              onClick={() => onPreview?.(template)}
              variant="ghost"
              size="sm"
              className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/20 hover:bg-white/30 text-white"
            >
              <Eye className="w-4 h-4" />
            </Button>
          </div>
        </div>

        <CardHeader className="pb-3">
          <div className="space-y-2">
            <CardTitle className="text-lg font-display line-clamp-2">
              {template.name}
            </CardTitle>
            <p className="text-sm text-gray-600 line-clamp-2">
              {template.description}
            </p>
          </div>
        </CardHeader>

        <CardContent className="space-y-4">
          {/* Template Structure */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700 flex items-center">
              <BookOpen className="w-4 h-4 mr-1" />
              Structure ({template.structure.sections.length} sections)
            </h4>
            <div className="space-y-1">
              {template.structure.sections.slice(0, 3).map((section, index) => (
                <div key={index} className="flex items-center justify-between text-xs">
                  <span className="text-gray-600 truncate">{section.name}</span>
                  <span className="text-gray-400">{section.word_count_guide}w</span>
                </div>
              ))}
              {template.structure.sections.length > 3 && (
                <div className="text-xs text-gray-400">
                  +{template.structure.sections.length - 3} more sections
                </div>
              )}
            </div>
          </div>

          {/* Richmond Elements */}
          <div className="space-y-2">
            <h4 className="text-sm font-medium text-gray-700">Richmond Elements</h4>
            <div className="flex flex-wrap gap-1">
              {template.structure.richmond_elements.slice(0, 3).map((element, index) => (
                <Badge key={index} variant="outline" className="text-xs">
                  {element}
                </Badge>
              ))}
              {template.structure.richmond_elements.length > 3 && (
                <Badge variant="outline" className="text-xs">
                  +{template.structure.richmond_elements.length - 3}
                </Badge>
              )}
            </div>
          </div>

          {/* Metadata */}
          <div className="flex items-center justify-between text-xs text-gray-500 pt-2 border-t border-gray-100">
            <div className="flex items-center space-x-1">
              <Clock className="w-3 h-3" />
              <span>{readingTime} min read</span>
            </div>
            <div className="flex items-center space-x-1">
              <Users className="w-3 h-3" />
              <span>{template.example_stories.length} examples</span>
            </div>
          </div>

          {/* Action Button */}
          <Button
            onClick={() => onSelect?.(template)}
            className="w-full mt-4"
            size="sm"
          >
            <Play className="w-4 h-4 mr-2" />
            Use Template
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  )
}

export default TemplateCard