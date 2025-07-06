import api from './api'
import { Session, Story, Template, Enhancement, ConversationResponse } from '@/types'

export const storyAPI = {
  // Conversation endpoints
  async startConversation(idea: string): Promise<Session> {
    const { data } = await api.post('/conversation/start', { core_idea: idea })
    return data
  },

  async continueConversation(sessionId: string, response: string): Promise<ConversationResponse> {
    const { data } = await api.post(`/conversation/continue/${sessionId}`, { user_response: response })
    return data
  },

  async selectOption(sessionId: string, optionType: string, index: number): Promise<void> {
    await api.post(`/conversation/select-option/${sessionId}`, {
      option_type: optionType,
      option_index: index,
    })
  },

  // Voice endpoints
  async uploadAudio(audio: Blob): Promise<{ transcription: string; sessionId?: string }> {
    const formData = new FormData()
    formData.append('audio', audio)
    
    const { data } = await api.post('/voice/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  },

  // Story endpoints
  async generateFinalStory(sessionId: string, style: string): Promise<Story> {
    const { data } = await api.post(`/conversation/generate-story/${sessionId}`, { style })
    return data
  },

  async enhanceStory(sessionId: string, enhancementType: string): Promise<Enhancement> {
    const { data } = await api.post('/features/enhance', {
      session_id: sessionId,
      enhancement_type: enhancementType,
    })
    return data
  },

  async exportStory(sessionId: string, format: string): Promise<Blob> {
    const { data } = await api.post('/features/export', {
      session_id: sessionId,
      format,
    }, {
      responseType: 'blob',
    })
    return data
  },

  // Template endpoints
  async getTemplates(): Promise<Template[]> {
    const { data } = await api.get('/features/templates')
    return data.templates
  },

  async applyTemplate(sessionId: string, templateId: string): Promise<void> {
    await api.post('/features/apply-template', {
      session_id: sessionId,
      template_id: templateId,
    })
  },

  // Session management
  async getSession(sessionId: string): Promise<Session> {
    const { data } = await api.get(`/conversation/session/${sessionId}`)
    return data
  },

  async getSessions(): Promise<Session[]> {
    const { data } = await api.get('/conversation/sessions')
    return data.sessions
  },
}