import { describe, it, expect, beforeEach, vi } from 'vitest'
import { AxiosError, AxiosHeaders } from 'axios'
import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { extractErrorMessage, AUTH_EXPIRED_EVENT, type ApiErrorBody } from './client'

// ── B5：extractErrorMessage 型別守衛 ────────────────────────────────────────
describe('extractErrorMessage — 四種 detail 形態', () => {
  function makeAxiosError(
    data: ApiErrorBody | undefined,
    status = 500,
    message = 'Request failed',
  ): AxiosError<ApiErrorBody> {
    const config = { headers: new AxiosHeaders() } as InternalAxiosRequestConfig
    const response: AxiosResponse<ApiErrorBody> | undefined =
      data === undefined
        ? undefined
        : {
            data,
            status,
            statusText: 'Error',
            headers: {},
            config,
          }
    return new AxiosError<ApiErrorBody>(message, 'ERR_BAD_RESPONSE', config, undefined, response)
  }

  it('detail 為 string 時直接回傳', () => {
    const err = makeAxiosError({ detail: '帳號不存在' })
    expect(extractErrorMessage(err)).toBe('帳號不存在')
  })

  it('detail 為 object 時取 message 欄位', () => {
    const err = makeAxiosError({ detail: { message: '驗證失敗', code: 'VALIDATION' } })
    expect(extractErrorMessage(err)).toBe('驗證失敗')
  })

  it('error.message 結構（自訂錯誤格式）', () => {
    const err = makeAxiosError({ error: { code: 'X', message: '伺服器錯誤' } })
    expect(extractErrorMessage(err)).toBe('伺服器錯誤')
  })

  it('detail 與 message 皆 undefined 時 fallback 至 axios 內建 message', () => {
    const err = makeAxiosError({}, 500, 'Network Error')
    expect(extractErrorMessage(err)).toBe('Network Error')
  })

  it('無 response（如網路錯誤）時 fallback 至 axios message', () => {
    const err = makeAxiosError(undefined, 0, 'timeout of 5000ms exceeded')
    expect(extractErrorMessage(err)).toBe('timeout of 5000ms exceeded')
  })

  it('非 AxiosError 但是 Error', () => {
    expect(extractErrorMessage(new Error('something'))).toBe('something')
  })

  it('完全未知型別', () => {
    expect(extractErrorMessage('string error')).toBe('未知錯誤')
  })
})

// ── B4：401 後派發 auth:expired 事件（不再硬寫 window.location） ────────────
describe('AUTH_EXPIRED_EVENT', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('事件常數為 auth:expired', () => {
    expect(AUTH_EXPIRED_EVENT).toBe('auth:expired')
  })

  it('可由 window.dispatchEvent 觸發訂閱者（與 AuthProvider 整合的契約）', () => {
    const listener = vi.fn()
    window.addEventListener(AUTH_EXPIRED_EVENT, listener)
    window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT))
    expect(listener).toHaveBeenCalledTimes(1)
    window.removeEventListener(AUTH_EXPIRED_EVENT, listener)
  })
})
