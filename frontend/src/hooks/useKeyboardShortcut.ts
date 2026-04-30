import { useEffect } from 'react'

export interface ShortcutOptions {
  meta?: boolean
  shift?: boolean
  alt?: boolean
  allowInInput?: boolean
}

const INPUT_TAGS = new Set(['INPUT', 'TEXTAREA', 'SELECT'])

export function useKeyboardShortcut(
  key: string,
  callback: () => void,
  options: ShortcutOptions = {}
): void {
  useEffect(() => {
    function handler(e: KeyboardEvent) {
      const target = e.target as HTMLElement | null
      if (!options.allowInInput && target && (INPUT_TAGS.has(target.tagName) || target.isContentEditable)) return
      if (e.key !== key) return
      if (options.meta && !(e.metaKey || e.ctrlKey)) return
      if (options.shift && !e.shiftKey) return
      if (options.alt && !e.altKey) return
      e.preventDefault()
      callback()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [key, callback, options.meta, options.shift, options.alt, options.allowInInput])
}
