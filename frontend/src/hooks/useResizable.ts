import { useCallback, useEffect, useRef, useState } from 'react'

export interface ResizableOptions {
  initial: number
  min: number
  max: number
  storageKey?: string
}

/**
 * I7：避免 width 出現在 effect 依賴造成事件監聽反覆掛載／移除。
 * 改以 widthRef 同步最新值，effect 只依賴設定（min/max/storageKey）。
 */
export function useResizable({ initial, min, max, storageKey }: ResizableOptions) {
  const initFromStorage = (): number => {
    if (!storageKey) return initial
    try {
      const v = Number(localStorage.getItem(storageKey))
      return Number.isFinite(v) && v >= min && v <= max ? v : initial
    } catch { return initial }
  }
  const [width, setWidth] = useState(initFromStorage)
  const widthRef = useRef(width)
  const dragging = useRef(false)
  const startX = useRef(0)
  const startW = useRef(0)

  useEffect(() => {
    widthRef.current = width
  }, [width])

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true
    startX.current = e.clientX
    startW.current = widthRef.current
  }, [])

  useEffect(() => {
    function onMove(e: MouseEvent) {
      if (!dragging.current) return
      const delta = startX.current - e.clientX
      const next = Math.max(min, Math.min(max, startW.current + delta))
      setWidth(next)
    }
    function onUp() {
      if (dragging.current && storageKey) {
        try { localStorage.setItem(storageKey, String(widthRef.current)) } catch { /* noop */ }
      }
      dragging.current = false
    }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', onUp)
    return () => {
      window.removeEventListener('mousemove', onMove)
      window.removeEventListener('mouseup', onUp)
    }
  }, [min, max, storageKey])

  return { width, onMouseDown }
}
