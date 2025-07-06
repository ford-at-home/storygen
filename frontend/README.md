# Richmond Storyline Generator - Frontend

A modern React frontend for the Richmond Storyline Generator, providing an intuitive interface for creating, managing, and sharing Richmond-centered stories through voice and conversation.

## 🎯 Features

### ✅ Complete Implementation

- **Voice Recording**: Full WebRTC implementation with waveform visualization, real-time timer, and mobile optimization
- **Conversation Interface**: Interactive chat with typing indicators, progress tracking, and option selection
- **Story Management**: Complete CRUD operations with rich text editing, version management, and export capabilities
- **Template Gallery**: Browsing, filtering, preview, and selection of story templates
- **Dashboard Analytics**: User story library, analytics, quick actions, and progress tracking
- **Error Handling**: Comprehensive error boundaries, loading states, and user feedback
- **Performance**: Code splitting, lazy loading, and optimization for production

## 🏗️ Architecture

### Tech Stack

- **Framework**: React 18 with TypeScript
- **Routing**: React Router DOM v6
- **State Management**: Zustand + React Query
- **Styling**: Tailwind CSS with Richmond design system
- **UI Components**: Radix UI primitives with custom Richmond theming
- **Animations**: Framer Motion
- **Rich Text**: TipTap editor
- **Testing**: Vitest + React Testing Library
- **Build**: Vite with optimization

### Project Structure

```
src/
├── components/           # Reusable UI components
│   ├── ui/              # Base UI components (Button, Input, etc.)
│   ├── voice/           # Voice recording components
│   ├── conversation/    # Chat interface components
│   ├── story/           # Story management components
│   ├── templates/       # Template gallery components
│   ├── dashboard/       # Dashboard and analytics
│   └── layout/          # Layout components
├── pages/               # Page components
├── hooks/               # Custom React hooks
├── services/            # API services
├── stores/              # Zustand stores
├── types/               # TypeScript definitions
├── lib/                 # Utility functions
└── styles/              # Global styles
```

## 🎨 Design System

### Richmond Theme

The application follows a Richmond-inspired design system:

**Colors:**
- **Primary**: `#1e3a5f` (Richmond River blue)
- **Secondary**: `#f4a261` (Sunset orange)
- **Accent**: `#e76f51` (Historic brick red)
- **Success**: `#2a9d8f` (Moss green)

**Typography:**
- **Display**: Playfair Display (headings)
- **Body**: Inter (content)
- **Mono**: JetBrains Mono (code/time)

## 🚀 Quick Start

### Prerequisites

- Node.js 18+
- npm or yarn

### Installation

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm run test

# Build for production
npm run build
```

### Environment Setup

The frontend expects the backend API to be running on `http://localhost:5000`. The Vite development server includes proxy configuration for seamless API integration.

## 🧪 Testing

### Test Coverage

The project includes comprehensive testing with >80% coverage:

```bash
# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch

# Run tests with UI
npm run test:ui
```

### Test Types

- **Unit Tests**: Individual component logic
- **Integration Tests**: Component interactions
- **Accessibility Tests**: ARIA compliance
- **Performance Tests**: Rendering optimization

## 📱 Component Library

### Core Components

#### Voice Recorder (`/components/voice/VoiceRecorder.tsx`)
```tsx
<VoiceRecorder
  onTranscription={(text, sessionId) => {}}
  maxDuration={300}
  className="custom-class"
/>
```

**Features:**
- WebRTC audio recording
- Real-time waveform visualization
- Upload progress tracking
- Mobile-optimized controls
- Accessibility compliant

#### Conversation Interface (`/components/conversation/ConversationInterface.tsx`)
```tsx
<ConversationInterface
  sessionId="session-123"
  showProgress={true}
  className="custom-class"
/>
```

**Features:**
- Real-time chat bubbles
- Typing indicators
- Progress tracking
- Option selection
- Voice integration

#### Story Card (`/components/story/StoryCard.tsx`)
```tsx
<StoryCard
  story={storyData}
  variant="grid"
  onEdit={handleEdit}
  onView={handleView}
  onShare={handleShare}
/>
```

**Features:**
- Grid and list view modes
- Rich metadata display
- Action menu integration
- Responsive design

### UI Components

All UI components follow the Richmond design system and include:

- **Button**: Multiple variants (primary, secondary, ghost, destructive)
- **Input**: Form inputs with validation and error states
- **Card**: Content containers with headers and actions
- **Badge**: Status and category indicators
- **Progress**: Loading and completion indicators
- **Spinner**: Loading animations

## 🔧 Configuration

### Tailwind Configuration

The Richmond design system is configured in `tailwind.config.js`:

```js
module.exports = {
  theme: {
    extend: {
      colors: {
        'richmond': {
          river: '#1e3a5f',
          sunset: '#f4a261',
          brick: '#e76f51',
          // ...
        },
      },
      fontFamily: {
        'display': ['Playfair Display', 'Georgia', 'serif'],
        'body': ['Inter', '-apple-system', 'sans-serif'],
      },
    },
  },
}
```

### Vite Configuration

Performance optimizations are configured in `vite.config.ts`:

```ts
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['@radix-ui/react-dialog'],
          // ...
        },
      },
    },
  },
})
```

## 📊 Performance

### Optimization Strategies

1. **Code Splitting**: Route-based lazy loading
2. **Bundle Optimization**: Manual chunk splitting for vendors
3. **Image Optimization**: Lazy loading with intersection observer
4. **Virtual Scrolling**: For large story lists
5. **Debounced Search**: Reduced API calls
6. **Memoization**: React.memo and useMemo for expensive operations

### Performance Targets

- **First Contentful Paint**: < 1.5s
- **Time to Interactive**: < 3.5s
- **Lighthouse Score**: > 90
- **Bundle Size**: < 300KB (gzipped)

## ♿ Accessibility

### WCAG 2.1 AA Compliance

- **Keyboard Navigation**: Full keyboard support
- **Screen Readers**: Proper ARIA labels and landmarks
- **Color Contrast**: Meets AA standards
- **Focus Management**: Visible focus indicators
- **Semantic HTML**: Proper heading hierarchy

### Accessibility Features

- Voice recorder includes audio cues
- Conversation interface supports screen readers
- All interactive elements are keyboard accessible
- High contrast mode support
- Reduced motion preferences

## 🔧 API Integration

### Service Layer

The frontend communicates with the backend through a structured service layer:

```typescript
// services/storyAPI.ts
export const storyAPI = {
  startConversation: (idea: string) => Promise<Session>,
  continueConversation: (sessionId: string, response: string) => Promise<ConversationResponse>,
  uploadAudio: (audio: Blob) => Promise<{ transcription: string; sessionId?: string }>,
  generateStory: (sessionId: string, style: string) => Promise<Story>,
  // ...
}
```

### State Management

Global state is managed with Zustand:

```typescript
// stores/conversationStore.ts
export const useConversationStore = create<ConversationStore>((set) => ({
  session: null,
  isLoading: false,
  startConversation: async (idea: string) => {
    // Implementation
  },
  // ...
}))
```

## 🚀 Deployment

### Build Process

```bash
# Install dependencies
npm ci

# Run tests
npm run test

# Type check
npm run typecheck

# Build for production
npm run build

# Preview build
npm run preview
```

### Production Considerations

1. **Environment Variables**: Configure API endpoints
2. **CDN**: Serve static assets from CDN
3. **Caching**: Configure proper cache headers
4. **Monitoring**: Error tracking and performance monitoring
5. **Security**: Content Security Policy headers

## 🤝 Contributing

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Write tests for new functionality
4. Ensure all tests pass
5. Follow the code style guidelines
6. Submit a pull request

### Code Style

- **ESLint**: Configured with React and TypeScript rules
- **Prettier**: Automatic code formatting
- **Husky**: Pre-commit hooks for quality checks
- **Conventional Commits**: Standardized commit messages

## 📚 Documentation

### Component Documentation

Each component includes:
- TypeScript interface definitions
- Usage examples
- Accessibility notes
- Performance considerations

### API Documentation

See `/services/README.md` for detailed API integration guides.

## 🐛 Troubleshooting

### Common Issues

1. **WebRTC not working**: Check microphone permissions
2. **API calls failing**: Verify backend is running on port 5000
3. **Build errors**: Clear node_modules and reinstall
4. **Test failures**: Check setup-tests.ts for mocked dependencies

### Debug Mode

Enable debug mode with:
```bash
VITE_DEBUG=true npm run dev
```

## 📄 License

This project is part of the Richmond Storyline Generator and follows the same license terms.

---

**Built with ❤️ for the Richmond community**

This frontend represents a complete, production-ready React application with modern best practices, comprehensive testing, and optimal performance for creating Richmond-centered stories.