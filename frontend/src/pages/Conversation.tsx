import React from 'react'
import { useParams } from 'react-router-dom'
import { ErrorBoundary } from '@/components/ui'
import { ConversationInterface } from '@/components/conversation'

export function Conversation() {
  const { sessionId } = useParams<{ sessionId?: string }>()

  return (
    <ErrorBoundary>
      <div className="min-h-screen bg-gray-50">
        <ConversationInterface 
          sessionId={sessionId}
          showProgress={true}
        />
      </div>
    </ErrorBoundary>
  )
}