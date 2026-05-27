/**
 * useDragScroll Hook
 * Enables horizontal scrolling by clicking and dragging with the mouse
 */
import { useEffect, useRef } from 'react'

export function useDragScroll() {
  const scrollRef = useRef(null)

  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    let isDown = false
    let startX
    let scrollLeft

    const onMouseDown = (e) => {
      // Skip if clicking on interactive elements
      const target = e.target
      if (target.tagName === 'BUTTON' || 
          target.tagName === 'INPUT' || 
          target.tagName === 'A' ||
          target.tagName === 'SELECT' ||
          target.closest('button') ||
          target.closest('input') ||
          target.closest('a') ||
          target.closest('select')) {
        return
      }

      isDown = true
      element.style.cursor = 'grabbing'
      element.style.userSelect = 'none'
      startX = e.pageX - element.offsetLeft
      scrollLeft = element.scrollLeft
    }

    const onMouseLeave = () => {
      isDown = false
      element.style.cursor = 'grab'
      element.style.userSelect = 'auto'
    }

    const onMouseUp = () => {
      isDown = false
      element.style.cursor = 'grab'
      element.style.userSelect = 'auto'
    }

    const onMouseMove = (e) => {
      if (!isDown) return
      e.preventDefault()
      const x = e.pageX - element.offsetLeft
      const walk = (x - startX) * 2 // Scroll speed multiplier
      element.scrollLeft = scrollLeft - walk
    }

    element.addEventListener('mousedown', onMouseDown)
    element.addEventListener('mouseleave', onMouseLeave)
    element.addEventListener('mouseup', onMouseUp)
    element.addEventListener('mousemove', onMouseMove)

    // Set initial cursor
    element.style.cursor = 'grab'
    element.style.scrollBehavior = 'auto'

    return () => {
      element.removeEventListener('mousedown', onMouseDown)
      element.removeEventListener('mouseleave', onMouseLeave)
      element.removeEventListener('mouseup', onMouseUp)
      element.removeEventListener('mousemove', onMouseMove)
    }
  }, [])

  return scrollRef
}
