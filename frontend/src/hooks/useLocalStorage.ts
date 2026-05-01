import { useCallback, useState } from 'react'

type Updater<T> = T | ((prev: T) => T)

/**
 * I10：setter 支援 functional updater（同 React useState）。
 */
export function useLocalStorage<T>(key: string, initial: T): [T, (v: Updater<T>) => void] {
  const [value, setValue] = useState<T>(() => {
    try {
      const raw = localStorage.getItem(key)
      return raw ? (JSON.parse(raw) as T) : initial
    } catch {
      return initial
    }
  })
  const set = useCallback((v: Updater<T>) => {
    setValue((prev) => {
      const next = typeof v === 'function' ? (v as (p: T) => T)(prev) : v
      try { localStorage.setItem(key, JSON.stringify(next)) } catch { /* noop */ }
      return next
    })
  }, [key])
  return [value, set]
}
