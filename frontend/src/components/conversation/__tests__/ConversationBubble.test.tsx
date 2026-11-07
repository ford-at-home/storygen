import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import ConversationBubble from '../ConversationBubble'
import { ConversationTurn } from '@/types'

describe('ConversationBubble Component', () => {
  const userTurn: ConversationTurn = {
    role: 'user',
    content: 'Hello, I want to write a story about Richmond.',
    timestamp: '2023-11-20T10:00:00Z',
  }

  const assistantTurn: ConversationTurn = {
    role: 'assistant',
    content: 'Great! I\'d love to help you create a Richmond story.',
    timestamp: '2023-11-20T10:01:00Z',
    metadata: {
      options: {
        angles: ['Historical', 'Modern', 'Personal'],
        tones: ['Casual', 'Formal', 'Nostalgic'],
      },
    },
  }

  const systemTurn: ConversationTurn = {
    role: 'system',
    content: 'Session started',
    timestamp: '2023-11-20T10:00:00Z',
  }

  it('renders user message with correct styling', () => {
    render(<ConversationBubble turn={userTurn} />)
    
    const bubble = screen.getByText(userTurn.content).closest('div')
    expect(bubble).toHaveClass('bg-richmond-river', 'text-white')
    expect(bubble?.parentElement).toHaveClass('justify-end')
  })

  it('renders assistant message with correct styling', () => {
    render(<ConversationBubble turn={assistantTurn} />)
    
    const bubble = screen.getByText(assistantTurn.content).closest('div')
    expect(bubble).toHaveClass('bg-white', 'border', 'text-gray-900')
    expect(bubble?.parentElement).toHaveClass('justify-start')
  })

  it('renders system message with correct styling', () => {
    render(<ConversationBubble turn={systemTurn} />)
    
    const bubble = screen.getByText(systemTurn.content).closest('div')
    expect(bubble).toHaveClass('bg-magnolia-cream', 'text-gray-700')
  })

  it('shows timestamp when requested', () => {
    render(<ConversationBubble turn={userTurn} showTimestamp />)
    
    expect(screen.getByText('10:00')).toBeInTheDocument()
  })

  it('renders options when present in metadata', () => {
    render(<ConversationBubble turn={assistantTurn} />)
    
    expect(screen.getByText('angles:')).toBeInTheDocument()
    expect(screen.getByText('Historical')).toBeInTheDocument()
    expect(screen.getByText('Modern')).toBeInTheDocument()
    expect(screen.getByText('Personal')).toBeInTheDocument()
    
    expect(screen.getByText('tones:')).toBeInTheDocument()
    expect(screen.getByText('Casual')).toBeInTheDocument()
    expect(screen.getByText('Formal')).toBeInTheDocument()
    expect(screen.getByText('Nostalgic')).toBeInTheDocument()
  })

  it('handles multiline content correctly', () => {
    const multilineTurn: ConversationTurn = {
      role: 'user',
      content: 'Line 1\nLine 2\nLine 3',
      timestamp: '2023-11-20T10:00:00Z',
    }

    render(<ConversationBubble turn={multilineTurn} />)
    
    const content = screen.getByText(/Line 1/)
    expect(content).toHaveClass('whitespace-pre-wrap')
  })

  it('applies custom className', () => {
    const { container } = render(
      <ConversationBubble turn={userTurn} className="custom-class" />
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })
})