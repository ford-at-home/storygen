import React, { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@radix-ui/react-tabs'
import { ErrorBoundary } from '@/components/ui'
import { StoryLibrary, Analytics, QuickActions } from '@/components/dashboard'
import { Story } from '@/types'
import { storyAPI } from '@/services/storyAPI'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'

const Dashboard: React.FC = () => {
  const [stories, setStories] = useState<Story[]>([])
  const [activeTab, setActiveTab] = useState('library')
  const navigate = useNavigate()

  useEffect(() => {
    const loadStories = async () => {
      try {
        const sessions = await storyAPI.getSessions()
        const completedStories = sessions
          .filter(session => session.story_elements?.final_story)
          .map(session => ({
            session_id: session.session_id,
            content: session.story_elements.final_story?.content || '',
            title: session.story_elements.final_story?.title,
            style: session.story_elements.final_story?.style || 'short_post',
            metadata: session.story_elements.final_story?.metadata || {
              word_count: 0,
              themes: [],
              tone: '',
              angle: '',
              richmond_context_used: 0,
            },
            created_at: session.created_at,
          }))
        
        setStories(completedStories)
      } catch (error) {
        toast.error('Failed to load stories')
      }
    }

    loadStories()
  }, [])

  const handleNewStory = () => {
    navigate('/record')
  }

  const handleStartVoiceStory = () => {
    navigate('/record')
  }

  const handleStartTextStory = () => {
    navigate('/conversation')
  }

  const handleBrowseTemplates = () => {
    navigate('/templates')
  }

  const handleEditStory = (story: Story) => {
    navigate(`/editor/${story.session_id}`)
  }

  const handleViewStory = (story: Story) => {
    navigate(`/story/${story.session_id}`)
  }

  const handleEnhanceStory = () => {
    if (stories.length === 0) {
      toast.error('Create a story first to enhance it')
      return
    }
    
    const latestStory = stories[0]
    navigate(`/editor/${latestStory.session_id}`)
  }

  const handleShareStory = async () => {
    if (stories.length === 0) {
      toast.error('Create a story first to share it')
      return
    }

    try {
      const latestStory = stories[0]
      await navigator.clipboard.writeText(`${window.location.origin}/story/${latestStory.session_id}`)
      toast.success('Story link copied to clipboard!')
    } catch (error) {
      toast.error('Failed to copy link')
    }
  }

  const handleExportStory = async () => {
    if (stories.length === 0) {
      toast.error('Create a story first to export it')
      return
    }

    try {
      const latestStory = stories[0]
      const blob = await storyAPI.exportStory(latestStory.session_id, 'pdf')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${latestStory.title || 'story'}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Story exported successfully!')
    } catch (error) {
      toast.error('Failed to export story')
    }
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
            className="mb-8"
          >
            <h1 className="text-4xl font-display font-bold text-gray-900 mb-2">
              Your Richmond Stories
            </h1>
            <p className="text-xl text-gray-600">
              Create, manage, and share your personalized Richmond narratives
            </p>
          </motion.div>

          <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
            <TabsList className="grid w-full grid-cols-3 lg:w-96">
              <TabsTrigger value="library">Story Library</TabsTrigger>
              <TabsTrigger value="analytics">Analytics</TabsTrigger>
              <TabsTrigger value="quick-actions">Quick Actions</TabsTrigger>
            </TabsList>

            <TabsContent value="library">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
              >
                <StoryLibrary
                  onNewStory={handleNewStory}
                  onEditStory={handleEditStory}
                  onViewStory={handleViewStory}
                />
              </motion.div>
            </TabsContent>

            <TabsContent value="analytics">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
              >
                <Analytics stories={stories} />
              </motion.div>
            </TabsContent>

            <TabsContent value="quick-actions">
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.3 }}
              >
                <QuickActions
                  onStartVoiceStory={handleStartVoiceStory}
                  onStartTextStory={handleStartTextStory}
                  onBrowseTemplates={handleBrowseTemplates}
                  onEnhanceStory={handleEnhanceStory}
                  onShareStory={handleShareStory}
                  onExportStory={handleExportStory}
                />
              </motion.div>
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </ErrorBoundary>
  )
}

export default Dashboard