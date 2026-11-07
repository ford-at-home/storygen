import React from 'react'
import { render, screen } from '@testing-library/react'
import '@testing-library/jest-dom'
import Analytics from '../Analytics'
import { Story } from '@/types'

describe('Analytics Component', () => {
  const mockStories: Story[] = [
    {
      session_id: 'story-1',
      content: 'First story content',
      title: 'First Story',
      style: 'short_post',
      metadata: {
        word_count: 100,
        themes: ['community', 'tech'],
        tone: 'casual',
        angle: 'personal',
        richmond_context_used: 3,
      },
      created_at: new Date().toISOString(),
    },
    {
      session_id: 'story-2',
      content: 'Second story content',
      title: 'Second Story',
      style: 'long_post',
      metadata: {
        word_count: 250,
        themes: ['history', 'culture'],
        tone: 'formal',
        angle: 'historical',
        richmond_context_used: 4,
      },
      created_at: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(), // Yesterday
    },
    {
      session_id: 'story-3',
      content: 'Third story content',
      title: 'Third Story',
      style: 'blog_post',
      metadata: {
        word_count: 500,
        themes: ['tech', 'innovation'],
        tone: 'professional',
        angle: 'business',
        richmond_context_used: 5,
      },
      created_at: new Date(Date.now() - 8 * 24 * 60 * 60 * 1000).toISOString(), // 8 days ago
    },
  ]

  it('renders analytics header', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText('Analytics')).toBeInTheDocument()
    expect(screen.getByText('Insights into your storytelling journey')).toBeInTheDocument()
  })

  it('displays correct total stories count', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText('3')).toBeInTheDocument()
    expect(screen.getByText('Total Stories')).toBeInTheDocument()
  })

  it('calculates total words correctly', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText('850')).toBeInTheDocument() // 100 + 250 + 500
    expect(screen.getByText('Total Words')).toBeInTheDocument()
  })

  it('calculates reading time correctly', () => {
    render(<Analytics stories={mockStories} />)
    
    const readingTime = Math.ceil(850 / 200) // 850 words at 200 words per minute
    expect(screen.getByText(`${readingTime} min`)).toBeInTheDocument()
    expect(screen.getByText('Reading Time')).toBeInTheDocument()
  })

  it('shows Richmond context usage', () => {
    render(<Analytics stories={mockStories} />)
    
    const avgContext = ((3 + 4 + 5) / 3) * 20 // Average of 4, converted to percentage
    expect(screen.getByText(`${Math.round(avgContext)}%`)).toBeInTheDocument()
    expect(screen.getByText('Richmond Context')).toBeInTheDocument()
  })

  it('displays recent activity for this week', () => {
    render(<Analytics stories={mockStories} />)
    
    // Should show 2 stories from this week (today and yesterday)
    expect(screen.getByText('+2 this week')).toBeInTheDocument()
  })

  it('shows story style breakdown', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText('Story Styles')).toBeInTheDocument()
    expect(screen.getByText('Short post')).toBeInTheDocument()
    expect(screen.getByText('Long post')).toBeInTheDocument()
    expect(screen.getByText('Blog post')).toBeInTheDocument()
  })

  it('displays popular themes', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText('Popular Themes')).toBeInTheDocument()
    expect(screen.getByText('tech')).toBeInTheDocument() // Appears twice
    expect(screen.getByText('community')).toBeInTheDocument()
    expect(screen.getByText('history')).toBeInTheDocument()
  })

  it('shows achievements section', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText('Achievements')).toBeInTheDocument()
    expect(screen.getByText('First Story')).toBeInTheDocument()
    expect(screen.getByText('Prolific Writer')).toBeInTheDocument()
    expect(screen.getByText('Word Master')).toBeInTheDocument()
    expect(screen.getByText('Richmond Expert')).toBeInTheDocument()
  })

  it('marks appropriate achievements as unlocked', () => {
    render(<Analytics stories={mockStories} />)
    
    // First Story should be unlocked (3 stories > 1)
    const firstStoryAchievement = screen.getByText('First Story').closest('div')
    expect(firstStoryAchievement).toHaveClass('bg-moss-green/10')
    
    // Richmond Expert should be unlocked (one story has 5 context sources)
    const richmondExpertAchievement = screen.getByText('Richmond Expert').closest('div')
    expect(richmondExpertAchievement).toHaveClass('bg-moss-green/10')
  })

  it('shows weekly summary', () => {
    render(<Analytics stories={mockStories} />)
    
    expect(screen.getByText("This Week's Summary")).toBeInTheDocument()
    expect(screen.getByText('Stories Created')).toBeInTheDocument()
    expect(screen.getByText('Words Written')).toBeInTheDocument()
    expect(screen.getByText('Avg Richmond Context')).toBeInTheDocument()
  })

  it('handles empty stories array', () => {
    render(<Analytics stories={[]} />)
    
    expect(screen.getByText('0')).toBeInTheDocument()
    expect(screen.getByText('Total Stories')).toBeInTheDocument()
    expect(screen.getByText('0 min')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<Analytics stories={mockStories} className="custom-class" />)
    
    expect(container.firstChild).toHaveClass('custom-class')
  })
})