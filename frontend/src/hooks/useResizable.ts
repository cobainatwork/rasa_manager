import { useCallback, useEffect, useRef, useState } from 'react'

export interface ResizableOptions {
  initial: number
  min: number
  max: number
  storageKey?: string
}

export function useResizable({ initial, min, max, storageKey }: ResizableOptions) {
  const initFromStorage = (): number => {
    if (!storageKey) return initial
    try {
      const v = Number(localStorage.getItem(storageKey))
      return Number.isFinite(v) && v >= min && v <= max ? v : initial
    } catch { return initial }
  }
  const [width, setWidth] = useState(initFromStorage)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startW = useRef(0)

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true
    startX.current = e.clientX
    startW.current = width
  }, [width])

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!dragging.current) return
      const delta = startX.current - e.clientX
      const next = Math.max(min, Math.min(max, startW.current + delta))
      setWidth(next)
    }
    function onUp() {
      if (dragging.current && storageKey) {
        try { localStorage.setItem(storageKey, String(width)) } catch { /* noop */ }
      }
      dragging.current = false
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [min, max, storageKey, width])

  return { width, onMouseDown }
}
