import { useEffect, useRef, useState } from 'react'

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export interface UseAutoSaveOptions { debounceMs?: number }
export interface UseAutoSaveResult {
  status: SaveStatus
  lastSavedAt: Date | null
  forceSave: () => Promise<void>
}

export function useAutoSave<T>(
  value: T,
  saveFn: (v: T) => Promise<void>,
  { debounceMs = 300 }: UseAutoSaveOptions = {}
): UseAutoSaveResult {
  const [status, setStatus] = useState<SaveStatus>('idle')
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const initial = useRef(true)
  const valueRef = useRef(value)

  // 同步 valueRef 至最新 value（不在 render 期間直接寫 ref）
  useEffect(() => {
    valueRef.current = value
  }, [value])

  async function doSave(v: T) {
    setStatus('saving')
    try {
      await saveFn(v)
      setStatus('saved')
      setLastSavedAt(new Date())
    } catch {
      setStatus('error')
    }
  }

  useEffect(() => {
    if (initial.current) { initial.current = false; return }
    const t = setTimeout(() => doSave(value), debounceMs)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, debounceMs])

  const forceSave = async () => doSave(valueRef.current)
  return { status, lastSavedAt, forceSave }
}
