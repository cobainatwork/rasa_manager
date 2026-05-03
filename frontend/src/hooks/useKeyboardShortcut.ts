import { useEffect, useRef } from 'react'

export interface ShortcutOptions {
  meta?: boolean
  shift?: boolean
  alt?: boolean
  allowInInput?: boolean
  /** I9：是否呼叫 preventDefault，預設 true 維持原行為 */
  preventDefault?: boolean
}

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

/**
 * I8：callback 改以 ref 存取，避免每次 render 都重建事件監聽。
 * I9：新增 preventDefault 選項。
 */
export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  options: ShortcutOptions = {}
): void {
  const callbackRef = useRef(callback)

  useEffect(() => {
    callbackRef.current = callback
  }, [callback])

  const { meta, shift, alt, allowInInput, preventDefault = true } = options

  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (!allowInInput && target && (INPUT_TAGS.has(target.tagName) || target.isContentEditable)) return
      if (e.key !== key) return
      if (meta && !(e.metaKey || e.ctrlKey)) return
      if (shift && !e.shiftKey) return
      if (alt && !e.altKey) return
      if (preventDefault) e.preventDefault()
      callbackRef.current()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [key, meta, shift, alt, allowInInput, preventDefault])
}
