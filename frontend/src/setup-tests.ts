import '@testing-library/jest-dom'

// Mock IntersectionObserver
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  observe() {}
  unobserve() {}
  disconnect() {}
}

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn(),
  })),
})

// Mock navigator.clipboard
Object.defineProperty(navigator, 'clipboard', {
  value: {
    writeText: jest.fn().mockResolvedValue(undefined),
    readText: jest.fn().mockResolvedValue(''),
  },
})

// Mock MediaRecorder
global.MediaRecorder = class MediaRecorder extends EventTarget {
  state = 'inactive'
  stream: MediaStream | null = null
  
  constructor(stream: MediaStream) {
    super()
    this.stream = stream
  }
  
  start() {
    this.state = 'recording'
    this.dispatchEvent(new Event('start'))
  }
  
  stop() {
    this.state = 'inactive'
    this.dispatchEvent(new Event('stop'))
  }
  
  pause() {
    this.state = 'paused'
  }
  
  resume() {
    this.state = 'recording'
  }
  
  requestData() {
    this.dispatchEvent(new BlobEvent('dataavailable', { data: new Blob() }))
  }
}

// Mock getUserMedia
Object.defineProperty(navigator, 'mediaDevices', {
  value: {
    getUserMedia: jest.fn().mockResolvedValue({
      getTracks: () => [],
    }),
  },
})

// Mock AudioContext
global.AudioContext = class AudioContext {
  createAnalyser() {
    return {
      fftSize: 256,
      frequencyBinCount: 128,
      connect: jest.fn(),
      getByteFrequencyData: jest.fn(),
    }
  }
  
  createMediaStreamSource() {
    return {
      connect: jest.fn(),
    }
  }
  
  close() {
    return Promise.resolve()
  }
}

// Mock URL.createObjectURL
global.URL.createObjectURL = jest.fn(() => 'blob:mock-url')
global.URL.revokeObjectURL = jest.fn()

// Mock requestAnimationFrame
global.requestAnimationFrame = jest.fn(cb => setTimeout(cb, 0))
global.cancelAnimationFrame = jest.fn()