import React from 'react'
import { motion } from 'framer-motion'
import { format } from 'date-fns'
import { 
  MoreVertical, 
  Edit3, 
  Share2, 
  Download, 
  Copy,
  Trash2,
  Eye,
  Calendar,
  FileText,
  Tag
} from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { Card, CardContent, CardHeader } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { Story } from '@/types'
import { cn } from '@/lib/utils'

interface StoryCardProps {
  story: Story
  variant?: 'grid' | 'list'
  onEdit?: (story: Story) => void
  onView?: (story: Story) => void
  onShare?: (story: Story) => void
  onExport?: (story: Story) => void
  onDelete?: (story: Story) => void
  className?: string
}

const StoryCard: React.FC<StoryCardProps> = ({
  story,
  variant = 'grid',
  onEdit,
  onView,
  onShare,
  onExport,
  onDelete,
  className,
}) => {
  const previewText = story.content.length > 150 
    ? story.content.substring(0, 150) + '...'
    : story.content

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(`${window.location.origin}/story/${story.session_id}`)
      // Toast notification would go here
    } catch (error) {
      console.error('Failed to copy link:', error)
    }
  }

  if (variant === 'list') {
    return (
      <motion.div
        className={cn('group', className)}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <Card className="hover:shadow-md transition-shadow duration-200">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0 mr-4">
                <div className="flex items-center space-x-3 mb-2">
                  {story.title && (
                    <h3 className="text-lg font-display font-semibold text-gray-900 truncate">
                      {story.title}
                    </h3>
                  )}
                  <Badge variant="secondary" className="text-xs">
                    {story.style}
                  </Badge>
                </div>
                
                <p className="text-gray-600 text-sm line-clamp-2 mb-3">
                  {previewText}
                </p>
                
                <div className="flex items-center space-x-4 text-xs text-gray-500">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-3 h-3" />
                    <span>{format(new Date(story.created_at), 'MMM d, yyyy')}</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <FileText className="w-3 h-3" />
                    <span>{story.metadata.word_count} words</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Tag className="w-3 h-3" />
                    <span>{story.metadata.themes.join(', ')}</span>
                  </div>
                </div>
              </div>
              
              <div className="flex items-center space-x-2">
                <Button
                  onClick={() => onView?.(story)}
                  variant="ghost"
                  size="sm"
                  className="opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <Eye className="w-4 h-4" />
                </Button>
                
                <DropdownMenu.Root>
                  <DropdownMenu.Trigger asChild>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <MoreVertical className="w-4 h-4" />
                    </Button>
                  </DropdownMenu.Trigger>
                  <DropdownMenu.Content className="w-48">
                    <DropdownMenuItems 
                      story={story}
                      onEdit={onEdit}
                      onShare={onShare}
                      onExport={onExport}
                      onDelete={onDelete}
                      onCopyLink={handleCopyLink}
                    />
                  </DropdownMenu.Content>
                </DropdownMenu.Root>
              </div>
            </div>
          </CardContent>
        </Card>
      </motion.div>
    )
  }

  return (
    <motion.div
      className={cn('group', className)}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
      whileHover={{ y: -2 }}
    >
      <Card className="h-full hover:shadow-lg transition-all duration-200 cursor-pointer">
        {/* Header Image Placeholder */}
        <div className="h-32 bg-gradient-to-br from-richmond-river to-richmond-sunset rounded-t-lg relative overflow-hidden">
          <div className="absolute inset-0 bg-black/20" />
          <div className="absolute bottom-3 left-3 right-3">
            <div className="flex items-center justify-between">
              <Badge variant="secondary" className="text-xs bg-white/90 text-gray-900">
                {story.style}
              </Badge>
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="opacity-0 group-hover:opacity-100 transition-opacity bg-white/20 hover:bg-white/30 text-white"
                  >
                    <MoreVertical className="w-4 h-4" />
                  </Button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Content className="w-48">
                  <DropdownMenuItems 
                    story={story}
                    onEdit={onEdit}
                    onShare={onShare}
                    onExport={onExport}
                    onDelete={onDelete}
                    onCopyLink={handleCopyLink}
                  />
                </DropdownMenu.Content>
              </DropdownMenu.Root>
            </div>
          </div>
        </div>

        <CardHeader className="pb-2">
          {story.title && (
            <h3 className="text-lg font-display font-semibold text-gray-900 line-clamp-2">
              {story.title}
            </h3>
          )}
        </CardHeader>

        <CardContent className="pt-0">
          <p className="text-gray-600 text-sm line-clamp-3 mb-4">
            {previewText}
          </p>

          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs text-gray-500">
              <div className="flex items-center space-x-1">
                <Calendar className="w-3 h-3" />
                <span>{format(new Date(story.created_at), 'MMM d')}</span>
              </div>
              <div className="flex items-center space-x-1">
                <FileText className="w-3 h-3" />
                <span>{story.metadata.word_count} words</span>
              </div>
            </div>

            {story.metadata.themes.length > 0 && (
              <div className="flex flex-wrap gap-1">
                {story.metadata.themes.slice(0, 3).map((theme, index) => (
                  <Badge key={index} variant="outline" className="text-xs">
                    {theme}
                  </Badge>
                ))}
                {story.metadata.themes.length > 3 && (
                  <Badge variant="outline" className="text-xs">
                    +{story.metadata.themes.length - 3} more
                  </Badge>
                )}
              </div>
            )}
          </div>

          <div className="flex space-x-2 mt-4 pt-4 border-t border-gray-100">
            <Button
              onClick={() => onView?.(story)}
              variant="outline"
              size="sm"
              className="flex-1"
            >
              <Eye className="w-3 h-3 mr-1" />
              View
            </Button>
            <Button
              onClick={() => onEdit?.(story)}
              variant="ghost"
              size="sm"
              className="flex-1"
            >
              <Edit3 className="w-3 h-3 mr-1" />
              Edit
            </Button>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  )
}

const DropdownMenuItems: React.FC<{
  story: Story
  onEdit?: (story: Story) => void
  onShare?: (story: Story) => void
  onExport?: (story: Story) => void
  onDelete?: (story: Story) => void
  onCopyLink?: () => void
}> = ({ story, onEdit, onShare, onExport, onDelete, onCopyLink }) => (
  <>
    <DropdownMenu.Item 
      className="flex items-center space-x-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-100"
      onClick={() => onEdit?.(story)}
    >
      <Edit3 className="w-4 h-4" />
      <span>Edit Story</span>
    </DropdownMenu.Item>
    
    <DropdownMenu.Item 
      className="flex items-center space-x-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-100"
      onClick={() => onShare?.(story)}
    >
      <Share2 className="w-4 h-4" />
      <span>Share</span>
    </DropdownMenu.Item>
    
    <DropdownMenu.Item 
      className="flex items-center space-x-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-100"
      onClick={onCopyLink}
    >
      <Copy className="w-4 h-4" />
      <span>Copy Link</span>
    </DropdownMenu.Item>
    
    <DropdownMenu.Item 
      className="flex items-center space-x-2 px-3 py-2 text-sm cursor-pointer hover:bg-gray-100"
      onClick={() => onExport?.(story)}
    >
      <Download className="w-4 h-4" />
      <span>Export</span>
    </DropdownMenu.Item>
    
    <DropdownMenu.Separator className="my-1 h-px bg-gray-200" />
    
    <DropdownMenu.Item 
      className="flex items-center space-x-2 px-3 py-2 text-sm cursor-pointer hover:bg-red-50 text-red-600"
      onClick={() => onDelete?.(story)}
    >
      <Trash2 className="w-4 h-4" />
      <span>Delete</span>
    </DropdownMenu.Item>
  </>
)

export default StoryCard