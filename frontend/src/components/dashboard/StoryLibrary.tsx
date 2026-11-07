import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Filter, Grid, List, Plus, SortAsc, SortDesc } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import { StoryCard } from '@/components/story'
import { Story } from '@/types'
import { storyAPI } from '@/services/storyAPI'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

interface StoryLibraryProps {
  onNewStory?: () => void
  onEditStory?: (story: Story) => void
  onViewStory?: (story: Story) => void
  className?: string
}

const StoryLibrary: React.FC<StoryLibraryProps> = ({
  onNewStory,
  onEditStory,
  onViewStory,
  className,
}) => {
  const [stories, setStories] = useState<Story[]>([])
  const [filteredStories, setFilteredStories] = useState<Story[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedFilter, setSelectedFilter] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [sortBy, setSortBy] = useState<'created_at' | 'title' | 'word_count'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')

  // Load stories
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
        setFilteredStories(completedStories)
      } catch (error) {
        toast.error('Failed to load stories')
      } finally {
        setIsLoading(false)
      }
    }

    loadStories()
  }, [])

  // Filter and sort stories
  useEffect(() => {
    let filtered = stories

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(
        story =>
          (story.title?.toLowerCase().includes(searchQuery.toLowerCase())) ||
          story.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
          story.metadata.themes.some(theme =>
            theme.toLowerCase().includes(searchQuery.toLowerCase())
          )
      )
    }

    // Filter by category
    if (selectedFilter !== 'all') {
      switch (selectedFilter) {
        case 'recent':
          const oneWeekAgo = new Date()
          oneWeekAgo.setDate(oneWeekAgo.getDate() - 7)
          filtered = filtered.filter(
            story => new Date(story.created_at) > oneWeekAgo
          )
          break
        case 'long':
          filtered = filtered.filter(story => story.metadata.word_count > 500)
          break
        case 'short':
          filtered = filtered.filter(story => story.metadata.word_count <= 200)
          break
        default:
          if (selectedFilter) {
            filtered = filtered.filter(story => story.style === selectedFilter)
          }
      }
    }

    // Sort stories
    filtered.sort((a, b) => {
      let comparison = 0
      
      switch (sortBy) {
        case 'created_at':
          comparison = new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
          break
        case 'title':
          comparison = (a.title || '').localeCompare(b.title || '')
          break
        case 'word_count':
          comparison = a.metadata.word_count - b.metadata.word_count
          break
      }

      return sortOrder === 'asc' ? comparison : -comparison
    })

    setFilteredStories(filtered)
  }, [stories, searchQuery, selectedFilter, sortBy, sortOrder])

  const filters = [
    { value: 'all', label: 'All Stories' },
    { value: 'recent', label: 'Recent' },
    { value: 'short_post', label: 'Short Posts' },
    { value: 'long_post', label: 'Long Posts' },
    { value: 'blog_post', label: 'Blog Posts' },
  ]

  const handleShare = async (story: Story) => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/story/${story.session_id}`)
      toast.success('Story link copied to clipboard!')
    } catch (error) {
      toast.error('Failed to copy link')
    }
  }

  const handleExport = async (story: Story) => {
    try {
      const blob = await storyAPI.exportStory(story.session_id, 'pdf')
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${story.title || 'story'}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      toast.success('Story exported successfully!')
    } catch (error) {
      toast.error('Failed to export story')
    }
  }

  const handleDelete = async (story: Story) => {
    if (!confirm('Are you sure you want to delete this story?')) return

    // Note: This would need a delete endpoint in the API
    setStories(prev => prev.filter(s => s.session_id !== story.session_id))
    toast.success('Story deleted')
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Spinner size="lg" />
      </div>
    )
  }

  return (
    <div className={cn('space-y-6', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-display font-bold text-gray-900">
            Your Stories
          </h2>
          <p className="text-gray-600 mt-1">
            {stories.length} story{stories.length !== 1 ? 's' : ''} in your library
          </p>
        </div>
        
        <Button onClick={onNewStory}>
          <Plus className="w-4 h-4 mr-2" />
          New Story
        </Button>
      </div>

      {/* Controls */}
      <div className="flex flex-col sm:flex-row gap-4">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <Input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search your stories..."
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex items-center space-x-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <select
            value={selectedFilter}
            onChange={(e) => setSelectedFilter(e.target.value)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-richmond-river focus:border-richmond-river"
          >
            {filters.map(filter => (
              <option key={filter.value} value={filter.value}>
                {filter.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-richmond-river focus:border-richmond-river"
          >
            <option value="created_at">Date</option>
            <option value="title">Title</option>
            <option value="word_count">Length</option>
          </select>
          
          <Button
            onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
            variant="outline"
            size="sm"
          >
            {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
          </Button>
        </div>

        <Button
          onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
          variant="outline"
          size="sm"
        >
          {viewMode === 'grid' ? <List className="w-4 h-4" /> : <Grid className="w-4 h-4" />}
        </Button>
      </div>

      {/* Results */}
      <AnimatePresence mode="wait">
        {filteredStories.length === 0 ? (
          <motion.div
            className="text-center py-12"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <div className="max-w-md mx-auto">
              <div className="text-gray-400 mb-4">
                <Search className="w-12 h-12 mx-auto" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">
                {searchQuery ? 'No stories found' : 'No stories yet'}
              </h3>
              <p className="text-gray-600 mb-4">
                {searchQuery 
                  ? 'Try adjusting your search or filters.'
                  : 'Start creating your first Richmond story!'
                }
              </p>
              {!searchQuery && (
                <Button onClick={onNewStory}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Your First Story
                </Button>
              )}
            </div>
          </motion.div>
        ) : (
          <motion.div
            key={viewMode}
            className={cn(
              'grid gap-6',
              viewMode === 'grid' 
                ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'
                : 'grid-cols-1'
            )}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {filteredStories.map((story, index) => (
              <motion.div
                key={story.session_id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <StoryCard
                  story={story}
                  variant={viewMode}
                  onEdit={onEditStory}
                  onView={onViewStory}
                  onShare={handleShare}
                  onExport={handleExport}
                  onDelete={handleDelete}
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}

export default StoryLibrary