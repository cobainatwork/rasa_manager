import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'

// ── baseURL 來源（B2）────────────────────────────────────────────────────────
// 由 VITE_API_BASE_URL 注入，預設為空字串：
// - 開發環境走 vite.config.ts proxy（/api → http://localhost:8000）。
// - 正式環境若部署在不同 host，可設為完整 URL；endpoint 內仍以 /api/v1 為前綴。
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export const apiClient = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

// ── FormData request interceptor ─────────────────────────────────────────────
// axios v1.x 當 instance 預設 Content-Type: application/json 時，
// 若請求 body 為 FormData 會執行 JSON.stringify(FormDataUtils.toJSON(data))，
// 導致 file 欄位被序列化為 {} 而非實際二進位（Content-Length 僅 11 bytes）。
// 在此攔截器移除 Content-Type，讓瀏覽器補上正確的 multipart/form-data; boundary=...。
apiClient.interceptors.request.use((config) => {
  if (config.data instanceof FormData) {
    config.headers.delete('Content-Type')
  }
  return config
})

// ── 401 失效事件（B4）────────────────────────────────────────────────────────
// 攔截器不再直接 window.location.href = '/login'（會丟掉 React Router 狀態），
// 改為派發 'auth:expired' 事件，由 AuthProvider 訂閱並使用 useNavigate 導向。
export const AUTH_EXPIRED_EVENT = 'auth:expired'

function dispatchAuthExpired() {
  if (typeof window === 'undefined') return
  window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
}

// ── 401 自動 refresh + pending promise queue ───────────────────────────────
let isRefreshing = false
let pendingQueue: Array<() => void> = []

function flushQueue() {
  pendingQueue.forEach((cb) => cb())
  pendingQueue = []
}

apiClient.interceptors.response.use(
  (resp: AxiosResponse) => resp,
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & {
      _retry?: boolean
    }

    if (!error.response || error.response.status !== 401 || originalRequest._retry) {
      return Promise.reject(error)
    }

    // /auth/login 與 /auth/refresh 的 401 不要重試（避免無限迴圈）
    if (
      originalRequest.url?.includes('/auth/login') ||
      originalRequest.url?.includes('/auth/refresh')
    ) {
      return Promise.reject(error)
    }

    if (isRefreshing) {
      return new Promise((resolve) => {
        pendingQueue.push(() => {
          originalRequest._retry = true
          resolve(apiClient(originalRequest))
        })
      })
    }

    originalRequest._retry = true
    isRefreshing = true

    try {
      await apiClient.post('/api/v1/auth/refresh')
      flushQueue()
      return apiClient(originalRequest)
    } catch (refreshErr) {
      pendingQueue = []
      // refresh 失敗 → 通知 AuthProvider 處理導頁，不再硬寫 window.location
      dispatchAuthExpired()
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  }
)

// ── 統一錯誤訊息提取（B5）──────────────────────────────────────────────────
// 後端錯誤格式（spec §13）：{ success: false, error: { code, message } } 或
// FastAPI 預設的 { detail: string | { message, code } }。
export interface ApiErrorBody {
  detail?: string | { message?: string; code?: string }
  message?: string
  error?: { code?: string; message?: string }
}

function isErrorBodyDetail(
  detail: unknown,
): detail is { message?: string; code?: string } {
  return typeof detail === 'object' && detail !== null && 'message' in detail
}

export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorBody>(error)) {
    const body = error.response?.data
    // 1. FastAPI HTTPException：detail 為 string
    if (typeof body?.detail === 'string') return body.detail
    // 2. FastAPI HTTPException：detail 為 object
    if (isErrorBodyDetail(body?.detail) && body.detail.message) {
      return body.detail.message
    }
    // 3. 自訂錯誤：{ error: { code, message } }
    if (body?.error?.message) return body.error.message
    // 4. 一般 message 欄位
    if (body?.message) return body.message
    // 5. fallback：axios 內建訊息（含網路錯誤）
    return error.message || '未知錯誤'
  }
  if (error instanceof Error) return error.message
  return '未知錯誤'
}
