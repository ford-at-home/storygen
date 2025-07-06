import React from 'react'
import { render, screen, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import StoryCard from '../StoryCard'
import { Story } from '@/types'

// Mock Radix UI components
jest.mock('@radix-ui/react-dropdown-menu', () => ({
  Root: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Trigger: ({ children, asChild }: { children: React.ReactNode; asChild?: boolean }) => 
    asChild ? children : <button>{children}</button>,
  Content: ({ children }: { children: React.ReactNode }) => <div data-testid="dropdown-content">{children}</div>,
  Item: ({ children, onClick }: { children: React.ReactNode; onClick?: () => void }) => 
    <div onClick={onClick} data-testid="dropdown-item">{children}</div>,
  Separator: () => <hr data-testid="dropdown-separator" />,
}))

describe('StoryCard Component', () => {
  const mockStory: Story = {
    session_id: 'test-session-1',
    content: 'This is a test story about Richmond that tells an interesting tale about the city and its people. It goes on to describe various aspects of the community.',
    title: 'A Richmond Adventure',
    style: 'short_post',
    metadata: {
      word_count: 150,
      themes: ['community', 'history', 'culture'],
      tone: 'casual',
      angle: 'personal',
      richmond_context_used: 3,
    },
    created_at: '2023-11-20T10:00:00Z',
  }

  const mockHandlers = {
    onEdit: jest.fn(),
    onView: jest.fn(),
    onShare: jest.fn(),
    onExport: jest.fn(),
    onDelete: jest.fn(),
  }

  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders story card in grid variant', () => {
    render(<StoryCard story={mockStory} variant="grid" {...mockHandlers} />)
    
    expect(screen.getByText('A Richmond Adventure')).toBeInTheDocument()
    expect(screen.getByText(/this is a test story about richmond/i)).toBeInTheDocument()
    expect(screen.getByText('150 words')).toBeInTheDocument()
    expect(screen.getByText('short_post')).toBeInTheDocument()
  })

  it('renders story card in list variant', () => {
    render(<StoryCard story={mockStory} variant="list" {...mockHandlers} />)
    
    expect(screen.getByText('A Richmond Adventure')).toBeInTheDocument()
    expect(screen.getByText(/this is a test story about richmond/i)).toBeInTheDocument()
  })

  it('shows themes as badges', () => {
    render(<StoryCard story={mockStory} {...mockHandlers} />)
    
    expect(screen.getByText('community')).toBeInTheDocument()
    expect(screen.getByText('history')).toBeInTheDocument()
    expect(screen.getByText('culture')).toBeInTheDocument()
  })

  it('truncates long content appropriately', () => {
    const longStory = {
      ...mockStory,
      content: 'This is a very long story that should be truncated because it exceeds the preview length limit. '.repeat(10),
    }

    render(<StoryCard story={longStory} {...mockHandlers} />)
    
    const preview = screen.getByText(/this is a very long story/i)
    expect(preview.textContent).toMatch(/\.\.\./)
  })

  it('calls onView when view button is clicked', () => {
    render(<StoryCard story={mockStory} {...mockHandlers} />)
    
    const viewButton = screen.getByText('View')
    fireEvent.click(viewButton)
    
    expect(mockHandlers.onView).toHaveBeenCalledWith(mockStory)
  })

  it('calls onEdit when edit button is clicked', () => {
    render(<StoryCard story={mockStory} {...mockHandlers} />)
    
    const editButton = screen.getByText('Edit')
    fireEvent.click(editButton)
    
    expect(mockHandlers.onEdit).toHaveBeenCalledWith(mockStory)
  })

  it('formats date correctly', () => {
    render(<StoryCard story={mockStory} {...mockHandlers} />)
    
    expect(screen.getByText('Nov 20')).toBeInTheDocument()
  })

  it('handles story without title', () => {
    const storyWithoutTitle = { ...mockStory, title: undefined }
    
    render(<StoryCard story={storyWithoutTitle} {...mockHandlers} />)
    
    // Should not crash and should still show content
    expect(screen.getByText(/this is a test story/i)).toBeInTheDocument()
  })

  it('shows limited themes with more indicator', () => {
    const storyWithManyThemes = {
      ...mockStory,
      metadata: {
        ...mockStory.metadata,
        themes: ['theme1', 'theme2', 'theme3', 'theme4', 'theme5'],
      },
    }

    render(<StoryCard story={storyWithManyThemes} {...mockHandlers} />)
    
    expect(screen.getByText('theme1')).toBeInTheDocument()
    expect(screen.getByText('theme2')).toBeInTheDocument()
    expect(screen.getByText('theme3')).toBeInTheDocument()
    expect(screen.getByText('+2 more')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <StoryCard story={mockStory} className="custom-class" {...mockHandlers} />
    )
    
    expect(container.firstChild).toHaveClass('custom-class')
  })
})