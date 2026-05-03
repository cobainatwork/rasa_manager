import type { AxiosResponse } from 'axios'
import type { ApiSuccess } from './types'

/**
 * I1：取代 endpoints 內散落的 `as T` 假型別斷言。
 * - 後端統一回應格式為 { success, data: T }（spec §13）。
 * - unwrap 將 AxiosResponse<ApiSuccess<T>> 展開為 T。
 * - fallback 參數可在 data 缺失時提供預設值（例如空陣列）。
 */
export async function unwrap<T>(
  promise: Promise<AxiosResponse<ApiSuccess<T>>>,
): Promise<T>
export async function unwrap<T>(
  promise: Promise<AxiosResponse<ApiSuccess<T>>>,
  fallback: T,
): Promise<T>
export async function unwrap<T>(
  promise: Promise<AxiosResponse<ApiSuccess<T>>>,
  fallback?: T,
): Promise<T> {
  const resp = await promise
  const data = resp.data?.data
  if (data === undefined || data === null) {
    if (fallback !== undefined) return fallback
    // 後端契約應保證 data 存在；若缺失視為協定錯誤
    throw new Error('API 回應缺少 data 欄位')
  }
  return data
}
