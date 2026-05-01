import { useEffect, useRef, useState } from 'react'

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error'

export interface UseAutoSaveOptions { debounceMs?: number }
export interface UseAutoSaveResult {
  status: SaveStatus
  lastSavedAt: Date | null
  lastError: Error | null
  forceSave: () => Promise<void>
}

/**
 * I5：將 saveFn 失敗保留為 lastError 以利上層顯示／重試。
 * I6：saveFn 改以 ref 存取，避免每次 render 都重建 effect。
 */
export function useAutoSave<T>(
  value: T,
  saveFn: (v: T) => Promise<void>,
  { debounceMs = 300 }: UseAutoSaveOptions = {}
): UseAutoSaveResult {
  const [status, setStatus] = useState<SaveStatus>('idle')
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null)
  const [lastError, setLastError] = useState<Error | null>(null)
  const initial = useRef(true)
  const valueRef = useRef(value)
  const saveFnRef = useRef(saveFn)

  useEffect(() => {
    valueRef.current = value
  }, [value])

  useEffect(() => {
    saveFnRef.current = saveFn
  }, [saveFn])

  async function doSave(v: T) {
    setStatus('saving')
    try {
      await saveFnRef.current(v)
      setStatus('saved')
      setLastSavedAt(new Date())
      setLastError(null)
    } catch (e) {
      const err = e instanceof Error ? e : new Error(String(e))
      setLastError(err)
      setStatus('error')
      console.error('[useAutoSave]', err)
    }
  }

  useEffect(() => {
    if (initial.current) { initial.current = false; return }
    const t = setTimeout(() => doSave(value), debounceMs)
    return () => clearTimeout(t)
    // saveFn 已透過 saveFnRef 取得最新引用，不需放在依賴中
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, debounceMs])

  const forceSave = async () => doSave(valueRef.current)
  return { status, lastSavedAt, lastError, forceSave }
}
