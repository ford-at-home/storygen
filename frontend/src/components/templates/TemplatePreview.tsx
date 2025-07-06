import React from 'react'
import { motion } from 'framer-motion'
import { X, Play, BookOpen, Clock, Target } from 'lucide-react'
import * as Dialog from '@radix-ui/react-dialog'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Template } from '@/types'
import { cn } from '@/lib/utils'

interface TemplatePreviewProps {
  template: Template
  onClose: () => void
  onSelect: () => void
}

const TemplatePreview: React.FC<TemplatePreviewProps> = ({
  template,
  onClose,
  onSelect,
}) => {
  const totalWordCount = template.structure.sections.reduce(
    (total, section) => total + section.word_count_guide, 
    0
  )

  const readingTime = Math.ceil(totalWordCount / 200)

  return (
    <Dialog.Root open onOpenChange={onClose}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/50 z-50" />
        <Dialog.Content className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-4xl h-[90vh] bg-white rounded-lg shadow-xl z-50 overflow-hidden">
          <motion.div
            className="h-full flex flex-col"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.2 }}
          >
            {/* Header */}
            <div className="flex items-center justify-between p-6 border-b border-gray-200">
              <div className="flex-1">
                <Dialog.Title className="text-2xl font-display font-bold text-gray-900">
                  {template.name}
                </Dialog.Title>
                <Dialog.Description className="text-gray-600 mt-1">
                  {template.description}
                </Dialog.Description>
              </div>
              
              <div className="flex items-center space-x-3">
                <Button onClick={onSelect} size="sm">
                  <Play className="w-4 h-4 mr-2" />
                  Use Template
                </Button>
                <Dialog.Close asChild>
                  <Button variant="ghost" size="sm">
                    <X className="w-4 h-4" />
                  </Button>
                </Dialog.Close>
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-auto p-6">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* Main Content */}
                <div className="lg:col-span-2 space-y-6">
                  {/* Template Structure */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <BookOpen className="w-5 h-5 mr-2" />
                        Template Structure
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {template.structure.sections.map((section, index) => (
                        <div
                          key={index}
                          className="flex items-start space-x-3 p-3 bg-gray-50 rounded-lg"
                        >
                          <div className="flex-shrink-0 w-8 h-8 bg-richmond-river text-white rounded-full flex items-center justify-center text-sm font-medium">
                            {index + 1}
                          </div>
                          <div className="flex-1">
                            <h4 className="font-medium text-gray-900">
                              {section.name}
                            </h4>
                            <p className="text-sm text-gray-600 mt-1">
                              {section.purpose}
                            </p>
                            <div className="flex items-center space-x-4 mt-2 text-xs text-gray-500">
                              <span>{section.word_count_guide} words</span>
                              <span>•</span>
                              <span>~{Math.ceil(section.word_count_guide / 200)} min</span>
                            </div>
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  {/* Prompts */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center">
                        <Target className="w-5 h-5 mr-2" />
                        Guided Prompts
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {template.structure.prompts.map((prompt, index) => (
                        <div
                          key={index}
                          className="p-3 bg-magnolia-cream rounded-lg border-l-4 border-richmond-sunset"
                        >
                          <p className="text-sm text-gray-700">
                            <span className="font-medium text-richmond-river">
                              Prompt {index + 1}:
                            </span>{' '}
                            {prompt}
                          </p>
                        </div>
                      ))}
                    </CardContent>
                  </Card>

                  {/* Example Stories */}
                  {template.example_stories.length > 0 && (
                    <Card>
                      <CardHeader>
                        <CardTitle>Example Stories</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        {template.example_stories.slice(0, 2).map((example, index) => (
                          <div
                            key={index}
                            className="p-4 bg-white border border-gray-200 rounded-lg"
                          >
                            <p className="text-sm text-gray-700 leading-relaxed">
                              "{example.substring(0, 200)}..."
                            </p>
                          </div>
                        ))}
                        {template.example_stories.length > 2 && (
                          <p className="text-sm text-gray-500 text-center">
                            +{template.example_stories.length - 2} more examples available
                          </p>
                        )}
                      </CardContent>
                    </Card>
                  )}
                </div>

                {/* Sidebar */}
                <div className="space-y-6">
                  {/* Template Stats */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Template Details</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Sections:</span>
                        <Badge variant="outline">
                          {template.structure.sections.length}
                        </Badge>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Total Length:</span>
                        <Badge variant="outline">
                          {totalWordCount} words
                        </Badge>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Reading Time:</span>
                        <div className="flex items-center space-x-1">
                          <Clock className="w-3 h-3 text-gray-400" />
                          <span className="text-sm">{readingTime} min</span>
                        </div>
                      </div>
                      
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-gray-600">Examples:</span>
                        <Badge variant="outline">
                          {template.example_stories.length}
                        </Badge>
                      </div>
                    </CardContent>
                  </Card>

                  {/* Richmond Elements */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Richmond Elements</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex flex-wrap gap-2">
                        {template.structure.richmond_elements.map((element, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {element}
                          </Badge>
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-3">
                        These elements will be emphasized in your story to create authentic Richmond context.
                      </p>
                    </CardContent>
                  </Card>

                  {/* Complexity Indicator */}
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Complexity Level</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-sm">Beginner</span>
                          <span className="text-sm">Advanced</span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="bg-gradient-to-r from-richmond-river to-richmond-sunset h-2 rounded-full transition-all duration-300"
                            style={{
                              width: `${Math.min(
                                (template.structure.sections.length / 8) * 100,
                                100
                              )}%`,
                            }}
                          />
                        </div>
                        <p className="text-xs text-gray-500">
                          Based on number of sections and prompts
                        </p>
                      </div>
                    </CardContent>
                  </Card>
                </div>
              </div>
            </div>

            {/* Footer */}
            <div className="border-t border-gray-200 p-6">
              <div className="flex items-center justify-between">
                <p className="text-sm text-gray-600">
                  This template will guide you through creating a compelling Richmond story with {template.structure.sections.length} structured sections.
                </p>
                <div className="flex items-center space-x-3">
                  <Button variant="outline" onClick={onClose}>
                    Close
                  </Button>
                  <Button onClick={onSelect}>
                    <Play className="w-4 h-4 mr-2" />
                    Start with Template
                  </Button>
                </div>
              </div>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}

export default TemplatePreview