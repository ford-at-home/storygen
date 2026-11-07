import React from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { Button } from '@/components/ui/Button'
import { ErrorBoundary } from '@/components/ui'
import { TemplateGallery } from '@/components/templates'
import { Template } from '@/types'
import { useConversationStore } from '@/stores/conversationStore'
import toast from 'react-hot-toast'

export function Templates() {
  const navigate = useNavigate()
  const { startConversation } = useConversationStore()

  const handleSelectTemplate = async (template: Template) => {
    try {
      // Start a conversation with template context
      const templatePrompt = `I want to create a story using the "${template.name}" template. ${template.description}`
      const sessionId = await startConversation(templatePrompt)
      
      if (sessionId) {
        navigate(`/conversation/${sessionId}`)
      }
    } catch (error) {
      toast.error('Failed to start story with template')
    }
  }

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        <div className="max-w-7xl mx-auto px-4 py-8">
          <div className="mb-8">
            <Button
              onClick={() => navigate(-1)}
              variant="ghost"
              className="mb-6"
            >
              <ArrowLeft className="w-4 h-4 mr-2" />
              Back
            </Button>
          </div>
          
          <TemplateGallery onSelectTemplate={handleSelectTemplate} />
        </div>
      </div>
    </ErrorBoundary>
  )
}