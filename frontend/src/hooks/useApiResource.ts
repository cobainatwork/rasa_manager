import { useCallback, useEffect, useRef, useState, type DependencyList } from 'react'
import { extractErrorMessage } from '@/api/client'

export interface UseApiResourceOptions<T> {
  /** 初始 loading 狀態，預設 true（資料尚未抵達） */
  initialLoading?: boolean
  /** 錯誤時將 data 重設為此值（避免畫面殘留舊資料），不設定則維持原值 */
  fallback?: T
  /** 失敗時是否額外 console.error，預設 false */
  logError?: boolean
  /** console.error 的 prefix（僅當 logError = true 時生效） */
  logPrefix?: string
  /** 跳過自動 fetch（讓 caller 用 reload 手動觸發），預設 false */
  skip?: boolean
  /** 失敗時的額外 callback（如 toast.error）— 在 race-condition 通過後才呼叫 */
  onError?: (err: unknown) => void
  /** 設為 true 時不寫入內部 error state（適合 toast 模式）；預設 false */
  silentError?: boolean
}

export interface UseApiResourceResult<T> {
  data: T | null
  loading: boolean
  error: string | null
  reload: () => void
}

/**
 * 統一處理「fetch + loading + error」樣板的 hook。
 *
 * 用法：
 * ```ts
 * const { data, loading, error, reload } = useApiResource(
 *   () => getAgentStats(agentId),
 *   [agentId],
 *   { fallback: null, logPrefix: '[useAgentStats]' },
 * )
 * ```
 *
 * 等價於 `useState` + `useEffect` + `.then/.catch/.finally`，但統一錯誤訊息提取與 race-condition 防護。
 */
export function useApiResource<T>(
  fetcher: () => Promise<T>,
  deps: DependencyList,
  opts: UseApiResourceOptions<T> = {},
): UseApiResourceResult<T> {
  const {
    initialLoading = true,
    fallback,
    logError = false,
    logPrefix,
    skip = false,
    onError,
    silentError = false,
  } = opts
  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(initialLoading)
  const [error, setError] = useState<string | null>(null)
  // 用 ref 追蹤最新請求，避免 stale promise 覆寫新資料
  const reqIdRef = useRef(0)
  // fetcher 透過 ref 持有，避免每次重渲染都觸發 effect（caller 通常傳 inline arrow function）
  const fetcherRef = useRef(fetcher)
  const onErrorRef = useRef(onError)
  useEffect(() => {
    fetcherRef.current = fetcher
    onErrorRef.current = onError
  })

  const run = useCallback(() => {
    const myId = ++reqIdRef.current
    setLoading(true)
    setError(null)
    fetcherRef.current()
      .then((value) => {
        if (myId !== reqIdRef.current) return
        setData(value)
      })
      .catch((err) => {
        if (myId !== reqIdRef.current) return
        if (logError) {
          console.error(logPrefix ?? '[useApiResource]', err)
        }
        if (!silentError) setError(extractErrorMessage(err))
        if (fallback !== undefined) setData(fallback)
        onErrorRef.current?.(err)
      })
      .finally(() => {
        if (myId !== reqIdRef.current) return
        setLoading(false)
      })
  }, [logError, logPrefix, fallback, silentError])

  useEffect(() => {
    if (skip) {
      setLoading(false)
      return
    }
    run()
    // run 不入 deps，依賴 caller 提供的 deps（與 useEffect 慣例一致）
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  return { data, loading, error, reload: run }
}
