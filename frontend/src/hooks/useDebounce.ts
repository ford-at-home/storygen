import { useState, useEffect } from 'react'

export const useDebounce = <T>(value: T, delay: number): T => {
  const [debouncedValue, setDebouncedValue] = useState<T>(value)

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value)
    }, delay)

    return () => {
      clearTimeout(handler)
    }
  }, [value, delay])

  return debouncedValue
}

export const useThrottle = <T>(value: T, limit: number): T => {
  const [throttledValue, setThrottledValue] = useState<T>(value)
  const [lastRan, setLastRan] = useState<number>(Date.now())

  useEffect(() => {
    const handler = setTimeout(() => {
      if (Date.now() - lastRan >= limit) {
        setThrottledValue(value)
        setLastRan(Date.now())
      }
    }, limit - (Date.now() - lastRan))

    return () => {
      clearTimeout(handler)
    }
  }, [value, limit, lastRan])

  return throttledValue
}