import { useState, useEffect } from 'react'

interface ImageOptimizationOptions {
  src: string
  placeholder?: string
  sizes?: string
  quality?: number
}

export const useImageOptimization = ({ 
  src, 
  placeholder, 
  quality = 80 
}: ImageOptimizationOptions) => {
  const [imageSrc, setImageSrc] = useState(placeholder || '')
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)

  useEffect(() => {
    if (!src) return

    setIsLoading(true)
    setHasError(false)

    const img = new Image()
    
    img.onload = () => {
      setImageSrc(src)
      setIsLoading(false)
    }
    
    img.onerror = () => {
      setHasError(true)
      setIsLoading(false)
      if (placeholder) {
        setImageSrc(placeholder)
      }
    }
    
    img.src = src
    
    return () => {
      img.onload = null
      img.onerror = null
    }
  }, [src, placeholder])

  return {
    src: imageSrc,
    isLoading,
    hasError,
  }
}

// Hook for lazy loading images with intersection observer
export const useLazyImage = (options: ImageOptimizationOptions) => {
  const [isIntersecting, setIsIntersecting] = useState(false)
  const [ref, setRef] = useState<HTMLElement | null>(null)

  useEffect(() => {
    if (!ref) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsIntersecting(true)
          observer.disconnect()
        }
      },
      {
        threshold: 0.1,
        rootMargin: '50px',
      }
    )

    observer.observe(ref)

    return () => observer.disconnect()
  }, [ref])

  const imageProps = useImageOptimization({
    ...options,
    src: isIntersecting ? options.src : '',
  })

  return {
    ...imageProps,
    ref: setRef,
    isIntersecting,
  }
}