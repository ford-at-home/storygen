import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Save, 
  Undo, 
  Redo, 
  Type, 
  Palette, 
  Sparkles, 
  Download,
  Share2,
  Eye,
  EyeOff,
  Settings
} from 'lucide-react'
import { useEditor, EditorContent } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { Badge } from '@/components/ui/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Progress } from '@/components/ui/Progress'
import { Story, Enhancement } from '@/types'
import { storyAPI } from '@/services/storyAPI'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

interface StoryEditorProps {
  story: Story
  onSave?: (updatedStory: Story) => void
  onExport?: (format: string) => void
  onShare?: () => void
  className?: string
}

const StoryEditor: React.FC<StoryEditorProps> = ({
  story,
  onSave,
  onExport,
  onShare,
  className,
}) => {
  const [title, setTitle] = useState(story.title || '')
  const [isPreviewMode, setIsPreviewMode] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [enhancements, setEnhancements] = useState<Enhancement[]>([])
  const [isLoadingEnhancements, setIsLoadingEnhancements] = useState(false)
  const [showEnhancementPanel, setShowEnhancementPanel] = useState(false)

  const editor = useEditor({
    extensions: [StarterKit],
    content: story.content,
    editorProps: {
      attributes: {
        class: 'prose prose-sm sm:prose lg:prose-lg xl:prose-xl mx-auto focus:outline-none min-h-[400px] p-4',
      },
    },
  })

  const wordCount = editor?.getText().length || 0
  const readingTime = Math.ceil(wordCount / 200) // 200 words per minute

  const handleSave = async () => {
    if (!editor) return

    setIsSaving(true)
    try {
      const updatedContent = editor.getHTML()
      const updatedStory = {
        ...story,
        title,
        content: updatedContent,
        metadata: {
          ...story.metadata,
          word_count: editor.getText().length,
        },
      }
      
      onSave?.(updatedStory)
      toast.success('Story saved successfully!')
    } catch (error) {
      toast.error('Failed to save story')
    } finally {
      setIsSaving(false)
    }
  }

  const handleEnhance = async (enhancementType: string) => {
    if (!story.session_id) return

    setIsLoadingEnhancements(true)
    try {
      const enhancement = await storyAPI.enhanceStory(story.session_id, enhancementType)
      setEnhancements(prev => [...prev, enhancement])
      toast.success('Enhancement suggestion generated!')
    } catch (error) {
      toast.error('Failed to generate enhancement')
    } finally {
      setIsLoadingEnhancements(false)
    }
  }

  const applyEnhancement = (enhancement: Enhancement) => {
    if (!editor) return

    // Insert enhancement at cursor position
    editor.commands.insertContent(enhancement.example || enhancement.description)
    toast.success('Enhancement applied!')
  }

  const enhancementTypes = [
    { type: 'dialogue', label: 'Add Dialogue', icon: Type },
    { type: 'sensory', label: 'Sensory Details', icon: Palette },
    { type: 'emotion', label: 'Emotional Depth', icon: Sparkles },
  ]

  if (!editor) {
    return <div>Loading editor...</div>
  }

  return (
    <div className={cn('flex flex-col h-full', className)}>
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 bg-white">
        <div className="flex items-center space-x-4">
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Story Title"
            className="text-lg font-medium border-none shadow-none p-0 h-auto"
          />
          <div className="flex items-center space-x-2 text-sm text-gray-500">
            <span>{wordCount} words</span>
            <span>•</span>
            <span>{readingTime} min read</span>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            onClick={() => setShowEnhancementPanel(!showEnhancementPanel)}
            variant="outline"
            size="sm"
          >
            <Sparkles className="w-4 h-4 mr-2" />
            Enhance
          </Button>

          <Button
            onClick={() => setIsPreviewMode(!isPreviewMode)}
            variant="outline"
            size="sm"
          >
            {isPreviewMode ? (
              <>
                <EyeOff className="w-4 h-4 mr-2" />
                Edit
              </>
            ) : (
              <>
                <Eye className="w-4 h-4 mr-2" />
                Preview
              </>
            )}
          </Button>

          <Button
            onClick={handleSave}
            disabled={isSaving}
            size="sm"
          >
            <Save className="w-4 h-4 mr-2" />
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Main Editor */}
        <div className="flex-1 flex flex-col">
          {/* Toolbar */}
          {!isPreviewMode && (
            <div className="flex items-center space-x-2 p-2 border-b border-gray-200 bg-gray-50">
              <Button
                onClick={() => editor.chain().focus().undo().run()}
                disabled={!editor.can().undo()}
                variant="ghost"
                size="sm"
              >
                <Undo className="w-4 h-4" />
              </Button>
              
              <Button
                onClick={() => editor.chain().focus().redo().run()}
                disabled={!editor.can().redo()}
                variant="ghost"
                size="sm"
              >
                <Redo className="w-4 h-4" />
              </Button>

              <div className="w-px h-6 bg-gray-300 mx-2" />

              <Button
                onClick={() => editor.chain().focus().toggleBold().run()}
                variant={editor.isActive('bold') ? 'default' : 'ghost'}
                size="sm"
              >
                B
              </Button>

              <Button
                onClick={() => editor.chain().focus().toggleItalic().run()}
                variant={editor.isActive('italic') ? 'default' : 'ghost'}
                size="sm"
              >
                I
              </Button>

              <div className="w-px h-6 bg-gray-300 mx-2" />

              <Button
                onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()}
                variant={editor.isActive('heading', { level: 2 }) ? 'default' : 'ghost'}
                size="sm"
              >
                H2
              </Button>

              <Button
                onClick={() => editor.chain().focus().toggleBulletList().run()}
                variant={editor.isActive('bulletList') ? 'default' : 'ghost'}
                size="sm"
              >
                •
              </Button>
            </div>
          )}

          {/* Editor Content */}
          <div className="flex-1 overflow-auto bg-white">
            {isPreviewMode ? (
              <motion.div
                className="prose prose-sm sm:prose lg:prose-lg xl:prose-xl mx-auto p-8 max-w-none"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: 0.3 }}
                dangerouslySetInnerHTML={{ __html: editor.getHTML() }}
              />
            ) : (
              <EditorContent editor={editor} />
            )}
          </div>
        </div>

        {/* Enhancement Panel */}
        <AnimatePresence>
          {showEnhancementPanel && (
            <motion.div
              className="w-80 border-l border-gray-200 bg-magnolia-cream"
              initial={{ width: 0, opacity: 0 }}
              animate={{ width: 320, opacity: 1 }}
              exit={{ width: 0, opacity: 0 }}
              transition={{ duration: 0.3 }}
            >
              <div className="p-4 space-y-4 overflow-auto h-full">
                <div className="flex items-center justify-between">
                  <h3 className="font-medium text-gray-900">Story Enhancements</h3>
                  <Button
                    onClick={() => setShowEnhancementPanel(false)}
                    variant="ghost"
                    size="sm"
                  >
                    ×
                  </Button>
                </div>

                {/* Enhancement Types */}
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-700">Add Enhancement</h4>
                  {enhancementTypes.map(({ type, label, icon: Icon }) => (
                    <Button
                      key={type}
                      onClick={() => handleEnhance(type)}
                      disabled={isLoadingEnhancements}
                      variant="outline"
                      size="sm"
                      className="w-full justify-start"
                    >
                      <Icon className="w-4 h-4 mr-2" />
                      {label}
                    </Button>
                  ))}
                </div>

                {/* Story Metadata */}
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Story Details</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Style:</span>
                      <Badge variant="outline">{story.style}</Badge>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Tone:</span>
                      <span className="font-medium">{story.metadata.tone}</span>
                    </div>
                    
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-gray-600">Angle:</span>
                      <span className="font-medium">{story.metadata.angle}</span>
                    </div>

                    <div className="space-y-1">
                      <div className="text-sm text-gray-600">Themes:</div>
                      <div className="flex flex-wrap gap-1">
                        {story.metadata.themes.map((theme, index) => (
                          <Badge key={index} variant="secondary" className="text-xs">
                            {theme}
                          </Badge>
                        ))}
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-sm text-gray-600">Richmond Context Used:</div>
                      <Progress 
                        value={(story.metadata.richmond_context_used / 5) * 100} 
                        className="h-2"
                      />
                      <div className="text-xs text-gray-500">
                        {story.metadata.richmond_context_used}/5 sources
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Applied Enhancements */}
                {enhancements.length > 0 && (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium text-gray-700">Suggestions</h4>
                    {enhancements.map((enhancement, index) => (
                      <Card key={index} className="p-3">
                        <div className="space-y-2">
                          <div className="flex items-center justify-between">
                            <Badge variant="outline" className="text-xs">
                              {enhancement.type}
                            </Badge>
                            <Button
                              onClick={() => applyEnhancement(enhancement)}
                              variant="ghost"
                              size="sm"
                              className="h-6 px-2 text-xs"
                            >
                              Apply
                            </Button>
                          </div>
                          <p className="text-xs text-gray-600">
                            {enhancement.description}
                          </p>
                          {enhancement.example && (
                            <p className="text-xs text-gray-800 bg-white p-2 rounded italic">
                              "{enhancement.example}"
                            </p>
                          )}
                        </div>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Footer Actions */}
      <div className="flex items-center justify-between p-4 border-t border-gray-200 bg-white">
        <div className="flex items-center space-x-2 text-sm text-gray-500">
          <Settings className="w-4 h-4" />
          <span>Auto-save enabled</span>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            onClick={() => onExport?.('pdf')}
            variant="outline"
            size="sm"
          >
            <Download className="w-4 h-4 mr-2" />
            Export
          </Button>

          <Button
            onClick={onShare}
            variant="outline"
            size="sm"
          >
            <Share2 className="w-4 h-4 mr-2" />
            Share
          </Button>
        </div>
      </div>
    </div>
  )
}

export default StoryEditor