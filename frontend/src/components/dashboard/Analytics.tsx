import React from 'react'
import { motion } from 'framer-motion'
import { 
  BarChart3, 
  TrendingUp, 
  Calendar, 
  Clock, 
  FileText, 
  Tag,
  Target,
  Award
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/Card'
import { Badge } from '@/components/ui/Badge'
import { Progress } from '@/components/ui/Progress'
import { Story } from '@/types'
import { format, subDays, eachDayOfInterval } from 'date-fns'

interface AnalyticsProps {
  stories: Story[]
  className?: string
}

const Analytics: React.FC<AnalyticsProps> = ({ stories, className }) => {
  // Calculate analytics
  const totalStories = stories.length
  const totalWords = stories.reduce((sum, story) => sum + story.metadata.word_count, 0)
  const averageWords = totalStories > 0 ? Math.round(totalWords / totalStories) : 0
  const totalReadingTime = Math.ceil(totalWords / 200) // 200 words per minute

  // Recent activity (last 7 days)
  const sevenDaysAgo = subDays(new Date(), 7)
  const recentStories = stories.filter(
    story => new Date(story.created_at) > sevenDaysAgo
  )

  // Story breakdown by style
  const styleBreakdown = stories.reduce((acc, story) => {
    acc[story.style] = (acc[story.style] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  // Theme frequency
  const themeFrequency = stories
    .flatMap(story => story.metadata.themes)
    .reduce((acc, theme) => {
      acc[theme] = (acc[theme] || 0) + 1
      return acc
    }, {} as Record<string, number>)

  const topThemes = Object.entries(themeFrequency)
    .sort(([, a], [, b]) => b - a)
    .slice(0, 5)

  // Daily activity for the past week
  const dailyActivity = eachDayOfInterval({
    start: sevenDaysAgo,
    end: new Date(),
  }).map(date => {
    const dayStories = stories.filter(
      story => format(new Date(story.created_at), 'yyyy-MM-dd') === format(date, 'yyyy-MM-dd')
    ).length
    return {
      date: format(date, 'MMM dd'),
      stories: dayStories,
    }
  })

  const maxDailyStories = Math.max(...dailyActivity.map(day => day.stories), 1)

  // Richmond context usage
  const avgRichmondContext = stories.length > 0 
    ? stories.reduce((sum, story) => sum + story.metadata.richmond_context_used, 0) / stories.length
    : 0

  const stats = [
    {
      icon: FileText,
      label: 'Total Stories',
      value: totalStories.toString(),
      change: `+${recentStories.length} this week`,
      changeType: 'positive' as const,
    },
    {
      icon: BarChart3,
      label: 'Total Words',
      value: totalWords.toLocaleString(),
      change: `${averageWords} avg per story`,
      changeType: 'neutral' as const,
    },
    {
      icon: Clock,
      label: 'Reading Time',
      value: `${totalReadingTime} min`,
      change: `${Math.ceil(averageWords / 200)} min avg`,
      changeType: 'neutral' as const,
    },
    {
      icon: Target,
      label: 'Richmond Context',
      value: `${Math.round(avgRichmondContext * 20)}%`,
      change: `${avgRichmondContext.toFixed(1)}/5 avg sources`,
      changeType: 'positive' as const,
    },
  ]

  return (
    <div className={className}>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h2 className="text-2xl font-display font-bold text-gray-900">
            Analytics
          </h2>
          <p className="text-gray-600 mt-1">
            Insights into your storytelling journey
          </p>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: index * 0.1 }}
            >
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center space-x-3">
                    <div className="p-2 bg-richmond-river/10 rounded-lg">
                      <stat.icon className="w-5 h-5 text-richmond-river" />
                    </div>
                    <div className="flex-1">
                      <p className="text-2xl font-bold text-gray-900">
                        {stat.value}
                      </p>
                      <p className="text-sm text-gray-600">
                        {stat.label}
                      </p>
                      <p className={`text-xs mt-1 ${
                        stat.changeType === 'positive' ? 'text-moss-green' :
                        stat.changeType === 'negative' ? 'text-richmond-brick' :
                        'text-gray-500'
                      }`}>
                        {stat.change}
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Daily Activity */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Calendar className="w-5 h-5 mr-2" />
                Daily Activity
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {dailyActivity.map((day, index) => (
                  <div key={day.date} className="flex items-center space-x-3">
                    <span className="text-sm text-gray-600 w-12">
                      {day.date}
                    </span>
                    <div className="flex-1">
                      <Progress
                        value={(day.stories / maxDailyStories) * 100}
                        className="h-2"
                      />
                    </div>
                    <span className="text-sm font-medium w-8 text-right">
                      {day.stories}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Story Styles */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <FileText className="w-5 h-5 mr-2" />
                Story Styles
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {Object.entries(styleBreakdown).map(([style, count]) => (
                  <div key={style} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <div className="w-3 h-3 bg-richmond-river rounded-full" />
                      <span className="text-sm capitalize">
                        {style.replace('_', ' ')}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm font-medium">{count}</span>
                      <span className="text-xs text-gray-500">
                        ({Math.round((count / totalStories) * 100)}%)
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Top Themes */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Tag className="w-5 h-5 mr-2" />
                Popular Themes
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {topThemes.map(([theme, count], index) => (
                  <div key={theme} className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{
                          backgroundColor: `hsla(${(index * 60) % 360}, 70%, 95%, 1)`,
                          borderColor: `hsla(${(index * 60) % 360}, 70%, 80%, 1)`,
                        }}
                      >
                        {theme}
                      </Badge>
                    </div>
                    <span className="text-sm font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Achievements */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <Award className="w-5 h-5 mr-2" />
                Achievements
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  {
                    title: 'First Story',
                    description: 'Created your first Richmond story',
                    unlocked: totalStories >= 1,
                    progress: Math.min(totalStories, 1),
                    target: 1,
                  },
                  {
                    title: 'Prolific Writer',
                    description: 'Written 10 stories',
                    unlocked: totalStories >= 10,
                    progress: Math.min(totalStories, 10),
                    target: 10,
                  },
                  {
                    title: 'Word Master',
                    description: 'Written 10,000 words total',
                    unlocked: totalWords >= 10000,
                    progress: Math.min(totalWords, 10000),
                    target: 10000,
                  },
                  {
                    title: 'Richmond Expert',
                    description: 'Used all 5 context sources in a story',
                    unlocked: stories.some(s => s.metadata.richmond_context_used >= 5),
                    progress: Math.max(...stories.map(s => s.metadata.richmond_context_used), 0),
                    target: 5,
                  },
                ].map((achievement, index) => (
                  <div
                    key={achievement.title}
                    className={`p-3 rounded-lg border ${
                      achievement.unlocked 
                        ? 'bg-moss-green/10 border-moss-green/30' 
                        : 'bg-gray-50 border-gray-200'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className={`text-sm font-medium ${
                        achievement.unlocked ? 'text-moss-green' : 'text-gray-700'
                      }`}>
                        {achievement.title}
                        {achievement.unlocked && (
                          <Award className="w-4 h-4 inline ml-1" />
                        )}
                      </h4>
                      <span className="text-xs text-gray-500">
                        {achievement.progress}/{achievement.target}
                      </span>
                    </div>
                    <p className="text-xs text-gray-600 mb-2">
                      {achievement.description}
                    </p>
                    <Progress
                      value={(achievement.progress / achievement.target) * 100}
                      className="h-1"
                    />
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Weekly Summary */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <TrendingUp className="w-5 h-5 mr-2" />
              This Week's Summary
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              <div className="text-center">
                <p className="text-2xl font-bold text-richmond-river">
                  {recentStories.length}
                </p>
                <p className="text-sm text-gray-600">Stories Created</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-richmond-sunset">
                  {recentStories.reduce((sum, story) => sum + story.metadata.word_count, 0)}
                </p>
                <p className="text-sm text-gray-600">Words Written</p>
              </div>
              <div className="text-center">
                <p className="text-2xl font-bold text-moss-green">
                  {recentStories.length > 0 
                    ? Math.round(recentStories.reduce((sum, story) => sum + story.metadata.richmond_context_used, 0) / recentStories.length * 20)
                    : 0}%
                </p>
                <p className="text-sm text-gray-600">Avg Richmond Context</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

export default Analytics