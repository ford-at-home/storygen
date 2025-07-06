import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ErrorBoundary, LoadingState } from '@/components/ui'
import { StoryEditor } from '@/components/story'
import { Story } from '@/types'
import { storyAPI } from '@/services/storyAPI'
import toast from 'react-hot-toast'

export function Editor() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [story, setStory] = useState<Story | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    const loadStory = async () => {
      if (!sessionId) {
        toast.error('No session ID provided')
        navigate('/dashboard')
        return
      }

      try {
        const session = await storyAPI.getSession(sessionId)
        if (session.story_elements?.final_story) {
          const storyData: Story = {
            session_id: session.session_id,
            content: session.story_elements.final_story.content,
            title: session.story_elements.final_story.title,
            style: session.story_elements.final_story.style || 'short_post',
            metadata: session.story_elements.final_story.metadata || {
              word_count: 0,
              themes: [],
              tone: '',
              angle: '',
              richmond_context_used: 0,
            },
            created_at: session.created_at,
          }
          setStory(storyData)
        } else {
          toast.error('No story found for this session')
          navigate('/dashboard')
        }
      } catch (error) {
        toast.error('Failed to load story')
        navigate('/dashboard')
      } finally {
        setIsLoading(false)
      }
    }

    loadStory()
  }, [sessionId, navigate])

  const handleSave = async (updatedStory: Story) => {
    // In a real implementation, this would save to the backend
    setStory(updatedStory)
    toast.success('Story saved successfully!')
  }

  const handleExport = async (format: string) => {
    if (!sessionId) return

    try {
      const blob = await storyAPI.exportStory(sessionId, format)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${story?.title || 'story'}.${format}`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success(`Story exported as ${format.toUpperCase()}!`)
    } catch (error) {
      toast.error('Failed to export story')
    }
  }

  const handleShare = async () => {
    if (!sessionId) return

    try {
      await navigator.clipboard.writeText(`${window.location.origin}/story/${sessionId}`)
      toast.success('Story link copied to clipboard!')
    } catch (error) {
      toast.error('Failed to copy link')
    }
  }

  if (isLoading) {
    return (
      <ErrorBoundary>
        <div className="min-h-screen bg-gray-50">
          <LoadingState
            title="Loading Story Editor"
            description="Preparing your story for editing..."
            variant="richmond"
          />
        </div>
      </ErrorBoundary>
    )
  }

  if (!story) {
    return (
      <ErrorBoundary>
        <div className="min-h-screen bg-gray-50">
          <div className="max-w-4xl mx-auto px-4 py-12 text-center">
            <h1 className="text-2xl font-bold text-gray-900 mb-4">
              Story Not Found
            </h1>
            <p className="text-gray-600 mb-6">
              The story you're looking for doesn't exist or couldn't be loaded.
            </p>
            <Button onClick={() => navigate('/dashboard')}>
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
        </div>
      </ErrorBoundary>
    )
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        <div className="h-screen flex flex-col">
          <div className="p-4 border-b border-gray-200 bg-white">
            <Button
              onClick={() => navigate('/dashboard')}
              variant="ghost"
              size="sm"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back to Dashboard
            </Button>
          </div>
          
          <div className="flex-1">
            <StoryEditor
              story={story}
              onSave={handleSave}
              onExport={handleExport}
              onShare={handleShare}
            />
          </div>
        </div>
      </div>
    </ErrorBoundary>
  )
}