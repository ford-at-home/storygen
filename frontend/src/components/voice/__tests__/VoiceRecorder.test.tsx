import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import '@testing-library/jest-dom'
import VoiceRecorder from '../VoiceRecorder'

// Mock the hook
jest.mock('../../hooks/useVoiceRecorder', () => ({
  useVoiceRecorder: () => ({
    isRecording: false,
    isPlaying: false,
    isProcessing: false,
    duration: 0,
    audioBlob: null,
    audioUrl: null,
    error: null,
    startRecording: jest.fn(),
    stopRecording: jest.fn(),
    reset: jest.fn(),
    getFrequencyData: jest.fn(() => new Uint8Array(0)),
  }),
}))

// Mock API
jest.mock('../../services/storyAPI', () => ({
  storyAPI: {
    uploadAudio: jest.fn(() => Promise.resolve({ 
      transcription: 'Test transcription',
      sessionId: 'test-session'
    })),
  },
}))

// Mock toast
jest.mock('react-hot-toast', () => ({
  __esModule: true,
  default: {
    success: jest.fn(),
    error: jest.fn(),
    warning: jest.fn(),
  },
}))

describe('VoiceRecorder Component', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('renders with initial state', () => {
    render(<VoiceRecorder />)
    
    expect(screen.getByText(/tap to start recording/i)).toBeInTheDocument()
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('shows recording state when recording', () => {
    const mockUseVoiceRecorder = require('../../hooks/useVoiceRecorder').useVoiceRecorder as jest.Mock
    mockUseVoiceRecorder.mockReturnValue({
      isRecording: true,
      isPlaying: false,
      isProcessing: false,
      duration: 5,
      audioBlob: null,
      audioUrl: null,
      error: null,
      startRecording: jest.fn(),
      stopRecording: jest.fn(),
      reset: jest.fn(),
      getFrequencyData: jest.fn(() => new Uint8Array(256)),
    })

    render(<VoiceRecorder />)
    
    expect(screen.getByText(/recording... tap to stop/i)).toBeInTheDocument()
    expect(screen.getByText('0:05')).toBeInTheDocument()
  })

  it('shows playback controls when recording is complete', () => {
    const audioBlob = new Blob(['audio data'], { type: 'audio/wav' })
    const audioUrl = 'blob:audio-url'
    
    const mockUseVoiceRecorder = require('../../hooks/useVoiceRecorder').useVoiceRecorder as jest.Mock
    mockUseVoiceRecorder.mockReturnValue({
      isRecording: false,
      isPlaying: false,
      isProcessing: false,
      duration: 10,
      audioBlob,
      audioUrl,
      error: null,
      startRecording: jest.fn(),
      stopRecording: jest.fn(),
      reset: jest.fn(),
      getFrequencyData: jest.fn(() => new Uint8Array(0)),
    })

    render(<VoiceRecorder />)
    
    expect(screen.getByText(/recording complete/i)).toBeInTheDocument()
    expect(screen.getByText(/process audio/i)).toBeInTheDocument()
  })

  it('calls onTranscription when upload is successful', async () => {
    const audioBlob = new Blob(['audio data'], { type: 'audio/wav' })
    const audioUrl = 'blob:audio-url'
    const mockOnTranscription = jest.fn()
    
    const mockUseVoiceRecorder = require('../../hooks/useVoiceRecorder').useVoiceRecorder as jest.Mock
    mockUseVoiceRecorder.mockReturnValue({
      isRecording: false,
      isPlaying: false,
      isProcessing: false,
      duration: 10,
      audioBlob,
      audioUrl,
      error: null,
      startRecording: jest.fn(),
      stopRecording: jest.fn(),
      reset: jest.fn(),
      getFrequencyData: jest.fn(() => new Uint8Array(0)),
    })

    render(<VoiceRecorder onTranscription={mockOnTranscription} />)
    
    const uploadButton = screen.getByText(/process audio/i)
    fireEvent.click(uploadButton)

    await waitFor(() => {
      expect(mockOnTranscription).toHaveBeenCalledWith('Test transcription', 'test-session')
    })
  })

  it('shows error message when there is an error', () => {
    const mockUseVoiceRecorder = require('../../hooks/useVoiceRecorder').useVoiceRecorder as jest.Mock
    mockUseVoiceRecorder.mockReturnValue({
      isRecording: false,
      isPlaying: false,
      isProcessing: false,
      duration: 0,
      audioBlob: null,
      audioUrl: null,
      error: 'Microphone access denied',
      startRecording: jest.fn(),
      stopRecording: jest.fn(),
      reset: jest.fn(),
      getFrequencyData: jest.fn(() => new Uint8Array(0)),
    })

    render(<VoiceRecorder />)
    
    expect(screen.getByText(/microphone access denied/i)).toBeInTheDocument()
  })

  it('respects maxDuration prop', () => {
    const maxDuration = 60 // 1 minute
    render(<VoiceRecorder maxDuration={maxDuration} />)
    
    expect(screen.getByText('Max: 1:00')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<VoiceRecorder className="custom-class" />)
    expect(container.firstChild).toHaveClass('custom-class')
  })
})