import { create } from 'zustand'
import { Session, ConversationStage } from '@/types'
import { storyAPI } from '@/services/storyAPI'
import toast from 'react-hot-toast'

interface ConversationStore {
  session: Session | null
  isLoading: boolean
  error: string | null

  // Actions
  startConversation: (idea: string) => Promise<string | null>
  continueConversation: (response: string) => Promise<void>
  selectOption: (optionType: string, index: number) => Promise<void>
  loadSession: (sessionId: string) => Promise<void>
  clearSession: () => void
}

export const useConversationStore = create<ConversationStore>((set, get) => ({
  session: null,
  isLoading: false,
  error: null,

  startConversation: async (idea: string) => {
    set({ isLoading: true, error: null })
    try {
      const session = await storyAPI.startConversation(idea)
      set({ session, isLoading: false })
      toast.success('Conversation started!')
      return session.session_id
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to start conversation'
      set({ error: errorMessage, isLoading: false })
      toast.error(errorMessage)
      return null
    }
  },

  continueConversation: async (response: string) => {
    const { session } = get()
    if (!session) return

    set({ isLoading: true, error: null })
    try {
      const result = await storyAPI.continueConversation(session.session_id, response)
      
      // Update session with new conversation turn
      const updatedSession = {
        ...session,
        current_stage: result.stage,
        conversation_history: [
          ...session.conversation_history,
          {
            role: 'user' as const,
            content: response,
            timestamp: new Date().toISOString(),
          },
          {
            role: 'assistant' as const,
            content: result.message,
            timestamp: new Date().toISOString(),
            metadata: result.options,
          },
        ],
      }

      if (result.story) {
        updatedSession.story_elements = {
          ...updatedSession.story_elements,
          final_story: result.story,
        }
      }

      set({ session: updatedSession, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to continue conversation'
      set({ error: errorMessage, isLoading: false })
      toast.error(errorMessage)
    }
  },

  selectOption: async (optionType: string, index: number) => {
    const { session } = get()
    if (!session) return

    set({ isLoading: true, error: null })
    try {
      await storyAPI.selectOption(session.session_id, optionType, index)
      
      // Reload session to get updated state
      await get().loadSession(session.session_id)
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to select option'
      set({ error: errorMessage, isLoading: false })
      toast.error(errorMessage)
    }
  },

  loadSession: async (sessionId: string) => {
    set({ isLoading: true, error: null })
    try {
      const session = await storyAPI.getSession(sessionId)
      set({ session, isLoading: false })
    } catch (error: any) {
      const errorMessage = error.response?.data?.error || 'Failed to load session'
      set({ error: errorMessage, isLoading: false })
      toast.error(errorMessage)
    }
  },

  clearSession: () => {
    set({ session: null, error: null })
  },
}))