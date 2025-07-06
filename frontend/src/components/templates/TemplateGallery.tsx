import React, { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Search, Filter, Grid, List, SortAsc, SortDesc } from 'lucide-react'
import { Input } from '@/components/ui/Input'
import { Button } from '@/components/ui/Button'
import { Badge } from '@/components/ui/Badge'
import { Spinner } from '@/components/ui/Spinner'
import TemplateCard from './TemplateCard'
import TemplatePreview from './TemplatePreview'
import { Template } from '@/types'
import { storyAPI } from '@/services/storyAPI'
import { cn } from '@/lib/utils'
import toast from 'react-hot-toast'

interface TemplateGalleryProps {
  onSelectTemplate?: (template: Template) => void
  className?: string
}

const TemplateGallery: React.FC<TemplateGalleryProps> = ({
  onSelectTemplate,
  className,
}) => {
  const [templates, setTemplates] = useState<Template[]>([])
  const [filteredTemplates, setFilteredTemplates] = useState<Template[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('all')
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
  const [sortBy, setSortBy] = useState<'name' | 'complexity' | 'popularity'>('name')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [previewTemplate, setPreviewTemplate] = useState<Template | null>(null)

  // Load templates
  useEffect(() => {
    const loadTemplates = async () => {
      try {
        const data = await storyAPI.getTemplates()
        setTemplates(data)
        setFilteredTemplates(data)
      } catch (error) {
        toast.error('Failed to load templates')
      } finally {
        setIsLoading(false)
      }
    }

    loadTemplates()
  }, [])

  // Filter and sort templates
  useEffect(() => {
    let filtered = templates

    // Filter by search query
    if (searchQuery) {
      filtered = filtered.filter(
        template =>
          template.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
          template.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          template.structure.richmond_elements.some(element =>
            element.toLowerCase().includes(searchQuery.toLowerCase())
          )
      )
    }

    // Filter by category
    if (selectedCategory !== 'all') {
      filtered = filtered.filter(template =>
        template.structure.richmond_elements.includes(selectedCategory)
      )
    }

    // Sort templates
    filtered.sort((a, b) => {
      let comparison = 0
      
      switch (sortBy) {
        case 'name':
          comparison = a.name.localeCompare(b.name)
          break
        case 'complexity':
          comparison = a.structure.sections.length - b.structure.sections.length
          break
        case 'popularity':
          comparison = a.example_stories.length - b.example_stories.length
          break
      }

      return sortOrder === 'asc' ? comparison : -comparison
    })

    setFilteredTemplates(filtered)
  }, [templates, searchQuery, selectedCategory, sortBy, sortOrder])

  const categories = ['all', ...Array.from(new Set(
    templates.flatMap(template => template.structure.richmond_elements)
  )).sort()]

  const handleSelectTemplate = async (template: Template) => {
    try {
      await storyAPI.applyTemplate('new-session', template.id)
      onSelectTemplate?.(template)
      toast.success(`${template.name} template applied!`)
    } catch (error) {
      toast.error('Failed to apply template')
    }
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
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-display font-bold text-gray-900">
              Story Templates
            </h1>
            <p className="text-gray-600 mt-1">
              Choose a template to guide your Richmond story creation
            </p>
          </div>
          
          <div className="flex items-center space-x-2">
            <Button
              onClick={() => setViewMode(viewMode === 'grid' ? 'list' : 'grid')}
              variant="outline"
              size="sm"
            >
              {viewMode === 'grid' ? <List className="w-4 h-4" /> : <Grid className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Filters and Search */}
        <div className="flex flex-col sm:flex-row gap-4">
          <div className="flex-1">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search templates..."
                className="pl-10"
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="border border-gray-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-richmond-river focus:border-richmond-river"
            >
              {categories.map(category => (
                <option key={category} value={category}>
                  {category === 'all' ? 'All Categories' : category}
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
              <option value="name">Name</option>
              <option value="complexity">Complexity</option>
              <option value="popularity">Popularity</option>
            </select>
            
            <Button
              onClick={() => setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')}
              variant="outline"
              size="sm"
            >
              {sortOrder === 'asc' ? <SortAsc className="w-4 h-4" /> : <SortDesc className="w-4 h-4" />}
            </Button>
          </div>
        </div>

        {/* Category Tags */}
        <div className="flex flex-wrap gap-2">
          {categories.slice(0, 8).map(category => (
            <Badge
              key={category}
              variant={selectedCategory === category ? 'default' : 'outline'}
              className="cursor-pointer"
              onClick={() => setSelectedCategory(category)}
            >
              {category === 'all' ? 'All' : category}
            </Badge>
          ))}
        </div>

        {/* Results Count */}
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            {filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''} found
          </span>
          {searchQuery && (
            <Button
              onClick={() => setSearchQuery('')}
              variant="ghost"
              size="sm"
            >
              Clear search
            </Button>
          )}
        </div>
      </div>

      {/* Templates Grid/List */}
      <AnimatePresence mode="wait">
        {filteredTemplates.length === 0 ? (
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
                No templates found
              </h3>
              <p className="text-gray-600">
                Try adjusting your search or filters to find the perfect template.
              </p>
            </div>
          </motion.div>
        ) : (
          <motion.div
            key={viewMode}
            className={cn(
              'grid gap-6',
              viewMode === 'grid' 
                ? 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4'
                : 'grid-cols-1'
            )}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
          >
            {filteredTemplates.map((template, index) => (
              <motion.div
                key={template.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3, delay: index * 0.1 }}
              >
                <TemplateCard
                  template={template}
                  onSelect={handleSelectTemplate}
                  onPreview={setPreviewTemplate}
                />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Template Preview Modal */}
      <AnimatePresence>
        {previewTemplate && (
          <TemplatePreview
            template={previewTemplate}
            onClose={() => setPreviewTemplate(null)}
            onSelect={() => {
              handleSelectTemplate(previewTemplate)
              setPreviewTemplate(null)
            }}
          />
        )}
      </AnimatePresence>
    </div>
  )
}

export default TemplateGallery