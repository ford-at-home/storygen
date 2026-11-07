import { ReactNode } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Mic, Home as HomeIcon, FileText, Layers, Edit3, LayoutDashboard } from 'lucide-react'
import { cn } from '@/lib/utils'

interface LayoutProps {
  children: ReactNode
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation()

  const navigation = [
    { name: 'Home', href: '/', icon: HomeIcon },
    { name: 'Record', href: '/record', icon: Mic },
    { name: 'Templates', href: '/templates', icon: Layers },
    { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  ]

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <Link to="/" className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-richmond-river rounded-lg flex items-center justify-center">
                <FileText className="w-6 h-6 text-white" />
              </div>
              <span className="font-display text-xl text-gray-900">Richmond Stories</span>
            </Link>
            
            <nav className="hidden md:flex space-x-8">
              {navigation.map((item) => {
                const Icon = item.icon
                const isActive = location.pathname === item.href
                return (
                  <Link
                    key={item.name}
                    to={item.href}
                    className={cn(
                      'flex items-center space-x-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'text-richmond-river'
                        : 'text-gray-600 hover:text-gray-900'
                    )}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </Link>
                )
              })}
            </nav>

            <button className="btn btn-primary">
              Start Your Story
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Navigation */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-50">
        <div className="grid grid-cols-4 gap-1 p-2">
          {navigation.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.href
            return (
              <Link
                key={item.name}
                to={item.href}
                className={cn(
                  'flex flex-col items-center justify-center py-2 px-3 rounded-lg transition-colors',
                  isActive
                    ? 'bg-richmond-river bg-opacity-10 text-richmond-river'
                    : 'text-gray-600 hover:text-gray-900'
                )}
              >
                <Icon className="w-5 h-5" />
                <span className="text-xs mt-1">{item.name}</span>
              </Link>
            )
          })}
        </div>
      </nav>

      {/* Main Content */}
      <main className="flex-1 pb-20 md:pb-0">
        {children}
      </main>
    </div>
  )
}