import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'

// 透過 Vite proxy 走 /api → http://localhost:8000
export const apiClient = axios.create({
  baseURL: '',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
})

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
      // refresh 失敗 → 導向登入頁
      if (typeof window !== 'undefined' && !window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
      return Promise.reject(refreshErr)
    } finally {
      isRefreshing = false
    }
  }
)

// ── 統一錯誤訊息提取 ──────────────────────────────────────────────────────
export function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (detail && typeof detail === 'object' && 'message' in detail) {
      return String(detail.message)
    }
    if (typeof detail === 'string') return detail
    return error.message || '未知錯誤'
  }
  if (error instanceof Error) return error.message
  return '未知錯誤'
}
