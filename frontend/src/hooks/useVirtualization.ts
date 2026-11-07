import { useState, useEffect, useMemo } from 'react'

interface VirtualizationOptions {
  items: any[]
  itemHeight: number
  containerHeight: number
  overscan?: number
}

export const useVirtualization = <T>({
  items,
  itemHeight,
  containerHeight,
  overscan = 5,
}: VirtualizationOptions) => {
  const [scrollTop, setScrollTop] = useState(0)

  const visibleRange = useMemo(() => {
    const visibleCount = Math.ceil(containerHeight / itemHeight)
    const startIndex = Math.floor(scrollTop / itemHeight)
    const endIndex = Math.min(
      startIndex + visibleCount + overscan,
      items.length - 1
    )

    return {
      start: Math.max(0, startIndex - overscan),
      end: endIndex,
    }
  }, [scrollTop, itemHeight, containerHeight, items.length, overscan])

  const visibleItems = useMemo(() => {
    return items.slice(visibleRange.start, visibleRange.end + 1).map((item, index) => ({
      item,
      index: visibleRange.start + index,
      top: (visibleRange.start + index) * itemHeight,
    }))
  }, [items, visibleRange, itemHeight])

  const totalHeight = items.length * itemHeight

  const handleScroll = (event: React.UIEvent<HTMLElement>) => {
    setScrollTop(event.currentTarget.scrollTop)
  }

  return {
    visibleItems,
    totalHeight,
    handleScroll,
    visibleRange,
  }
}

// Hook for infinite scrolling
export const useInfiniteScroll = <T>(
  items: T[],
  fetchMore: () => Promise<void>,
  hasMore: boolean = true,
  threshold: number = 100
) => {
  const [isLoading, setIsLoading] = useState(false)

  const handleScroll = async (event: React.UIEvent<HTMLElement>) => {
    const { scrollTop, scrollHeight, clientHeight } = event.currentTarget

    if (
      scrollHeight - scrollTop - clientHeight < threshold &&
      hasMore &&
      !isLoading
    ) {
      setIsLoading(true)
      try {
        await fetchMore()
      } catch (error) {
        console.error('Failed to load more items:', error)
      } finally {
        setIsLoading(false)
      }
    }
  }

  return {
    handleScroll,
    isLoading,
  }
}