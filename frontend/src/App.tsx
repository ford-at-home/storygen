import React, { Suspense } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { ErrorBoundary, LoadingState } from '@/components/ui'
import Layout from '@/components/layout/Layout'

// Lazy load pages for code splitting
const Home = React.lazy(() => import('@/pages/Home'))
const Dashboard = React.lazy(() => import('@/pages/Dashboard'))
const Record = React.lazy(() => import('@/pages/Record').then(module => ({ default: module.Record })))
const Conversation = React.lazy(() => import('@/pages/Conversation').then(module => ({ default: module.Conversation })))
const Templates = React.lazy(() => import('@/pages/Templates').then(module => ({ default: module.Templates })))
const Editor = React.lazy(() => import('@/pages/Editor').then(module => ({ default: module.Editor })))

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

const AppRoutes: React.FC = () => (
  <Routes>
    <Route path="/" element={<Home />} />
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/record" element={<Record />} />
    <Route path="/conversation" element={<Conversation />} />
    <Route path="/conversation/:sessionId" element={<Conversation />} />
    <Route path="/templates" element={<Templates />} />
    <Route path="/editor/:sessionId" element={<Editor />} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>
)

const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <Router>
          <Layout>
            <Suspense 
              fallback={
                <LoadingState
                  title="Loading Richmond Stories"
                  description="Preparing your storytelling experience..."
                  variant="richmond"
                  size="lg"
                />
              }
            >
              <AppRoutes />
            </Suspense>
          </Layout>
          <Toaster
            position="bottom-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#fff',
                color: '#1f2937',
                border: '1px solid #e5e7eb',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
              },
              success: {
                iconTheme: {
                  primary: '#2a9d8f',
                  secondary: '#fff',
                },
              },
              error: {
                iconTheme: {
                  primary: '#e76f51',
                  secondary: '#fff',
                },
              },
            }}
          />
        </Router>
      </QueryClientProvider>
    </ErrorBoundary>
  )
}

export default App