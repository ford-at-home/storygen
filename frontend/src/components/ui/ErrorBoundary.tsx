import React, { Component, ErrorInfo, ReactNode } from 'react'
import { motion } from 'framer-motion'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'
import { Button } from './Button'
import { Card, CardContent, CardHeader, CardTitle } from './Card'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  onError?: (error: Error, errorInfo: ErrorInfo) => void
}

interface State {
  hasError: boolean
  error?: Error
  errorInfo?: ErrorInfo
}

class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo })
    this.props.onError?.(error, errorInfo)
    
    // Log to error reporting service in production
    if (process.env.NODE_ENV === 'production') {
      console.error('Error caught by boundary:', error, errorInfo)
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: undefined, errorInfo: undefined })
  }

  handleGoHome = () => {
    window.location.href = '/'
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.3 }}
            className="w-full max-w-md"
          >
            <Card>
              <CardHeader className="text-center">
                <div className="mx-auto w-12 h-12 bg-richmond-brick/10 rounded-full flex items-center justify-center mb-4">
                  <AlertTriangle className="w-6 h-6 text-richmond-brick" />
                </div>
                <CardTitle className="text-xl">Something went wrong</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-gray-600 text-center">
                  We're sorry, but something unexpected happened. Our team has been notified and we're working to fix this issue.
                </p>

                {process.env.NODE_ENV === 'development' && this.state.error && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm text-gray-500 mb-2">
                      Technical Details (Development Only)
                    </summary>
                    <div className="bg-gray-100 p-3 rounded text-xs font-mono text-gray-700 whitespace-pre-wrap">
                      {this.state.error.toString()}
                      {this.state.errorInfo?.componentStack}
                    </div>
                  </details>
                )}

                <div className="flex space-x-3">
                  <Button
                    onClick={this.handleRetry}
                    variant="primary"
                    className="flex-1"
                  >
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Try Again
                  </Button>
                  <Button
                    onClick={this.handleGoHome}
                    variant="outline"
                    className="flex-1"
                  >
                    <Home className="w-4 h-4 mr-2" />
                    Go Home
                  </Button>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        </div>
      )
    }

    return this.props.children
  }
}

export default ErrorBoundary