export interface Session {
  session_id: string
  user_id?: string
  current_stage: ConversationStage
  story_elements: StoryElements
  conversation_history: ConversationTurn[]
  created_at: string
  updated_at: string
}

export enum ConversationStage {
  KICKOFF = 'kickoff',
  DEPTH_ANALYSIS = 'depth_analysis',
  ANGLE_SELECTION = 'angle_selection',
  TONE_SELECTION = 'tone_selection',
  LENGTH_SELECTION = 'length_selection',
  READY_TO_GENERATE = 'ready_to_generate',
  STORY_GENERATED = 'story_generated',
}

export interface StoryElements {
  core_idea?: string
  themes?: string[]
  angle?: string
  tone?: string
  length?: string
  context?: string[]
  enhancements?: Enhancement[]
}

export interface ConversationTurn {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface ConversationResponse {
  message: string
  stage: ConversationStage
  options?: ConversationOptions
  story?: Story
}

export interface ConversationOptions {
  angles?: string[]
  tones?: string[]
  lengths?: string[]
}

export interface Story {
  session_id: string
  content: string
  title?: string
  style: string
  metadata: StoryMetadata
  created_at: string
}

export interface StoryMetadata {
  word_count: number
  themes: string[]
  tone: string
  angle: string
  richmond_context_used: number
}

export interface Template {
  id: string
  name: string
  description: string
  structure: TemplateStructure
  example_stories: string[]
}

export interface TemplateStructure {
  sections: TemplateSection[]
  prompts: string[]
  richmond_elements: string[]
}

export interface TemplateSection {
  name: string
  purpose: string
  word_count_guide: number
}

export interface Enhancement {
  type: string
  description: string
  suggestions: string[]
  example?: string
}