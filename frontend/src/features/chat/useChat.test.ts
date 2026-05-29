import { renderHook, act, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { http, HttpResponse } from 'msw'
import { server } from '@/mocks/server'
import { useChat } from './useChat'

vi.mock('sonner', () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

const AGENT_ID = 'agent-1'

describe('useChat', () => {
  beforeEach(async () => {
    const { toast } = await import('sonner')
    vi.mocked(toast.error).mockClear()
  })

  describe('send', () => {
    it('成功時把 user 與 bot 訊息加入 messages，sending 結束為 false', async () => {
      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })

      expect(result.current.messages).toHaveLength(2)
      expect(result.current.messages[0]).toMatchObject({ role: 'user', text: '你好' })
      expect(result.current.messages[1]).toMatchObject({ role: 'bot', text: '測試回覆' })
      expect(result.current.sending).toBe(false)
    })

    it('失敗時保留 user 訊息但無 bot，toast.error 被呼叫', async () => {
      const { toast } = await import('sonner')
      server.use(
        http.post('/api/v1/agents/:id/chat/test', () =>
          HttpResponse.json(
            { detail: { code: 'BAD_GATEWAY', message: 'Rasa 連線失敗' } },
            { status: 502 },
          ),
        ),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })

      expect(result.current.messages).toHaveLength(1)
      expect(result.current.messages[0].role).toBe('user')
      expect(result.current.sending).toBe(false)
      expect(toast.error).toHaveBeenCalled()
    })

    it('agentId 為 undefined 時不發送請求且不更新 messages', async () => {
      const { result } = renderHook(() => useChat(undefined))

      await act(async () => {
        await result.current.send('你好')
      })

      expect(result.current.messages).toHaveLength(0)
    })

    it('空字串訊息不發送請求', async () => {
      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('   ')
      })

      expect(result.current.messages).toHaveLength(0)
    })
  })

  describe('clear', () => {
    it('成功時呼叫 chat/reset 端點並清空訊息', async () => {
      let resetUrl: string | null = null
      server.use(
        http.post('/api/v1/agents/:id/chat/reset', ({ request }) => {
          resetUrl = new URL(request.url).pathname
          return HttpResponse.json({ success: true })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })
      expect(result.current.messages.length).toBeGreaterThan(0)

      await act(async () => {
        await result.current.clear()
      })

      expect(resetUrl).toBe(`/api/v1/agents/${AGENT_ID}/chat/reset`)
      expect(result.current.messages).toHaveLength(0)
      expect(result.current.resetting).toBe(false)
    })

    it('reset 失敗時保留訊息並 toast.error', async () => {
      const { toast } = await import('sonner')
      server.use(
        http.post('/api/v1/agents/:id/chat/reset', () =>
          HttpResponse.json(
            { detail: { code: 'BAD_GATEWAY', message: '重置失敗' } },
            { status: 502 },
          ),
        ),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })
      const lenBefore = result.current.messages.length
      expect(lenBefore).toBeGreaterThan(0)

      await act(async () => {
        await result.current.clear()
      })

      expect(result.current.messages).toHaveLength(lenBefore)
      expect(result.current.resetting).toBe(false)
      expect(toast.error).toHaveBeenCalled()
    })

    it('clear 執行期間 resetting 為 true，完成後為 false', async () => {
      let resolveReset!: () => void
      server.use(
        http.post('/api/v1/agents/:id/chat/reset', async () => {
          await new Promise<void>((r) => {
            resolveReset = r
          })
          return HttpResponse.json({ success: true })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      let clearPromise!: Promise<void>
      act(() => {
        clearPromise = result.current.clear()
      })

      await waitFor(() => expect(result.current.resetting).toBe(true))

      resolveReset()
      await act(async () => {
        await clearPromise
      })

      expect(result.current.resetting).toBe(false)
    })

    it('agentId 為 undefined 時不呼叫 reset', async () => {
      let called = false
      server.use(
        http.post('/api/v1/agents/:id/chat/reset', () => {
          called = true
          return HttpResponse.json({ success: true })
        }),
      )

      const { result } = renderHook(() => useChat(undefined))

      await act(async () => {
        await result.current.clear()
      })

      expect(called).toBe(false)
      expect(result.current.resetting).toBe(false)
    })
  })

  describe('restart', () => {
    it('成功時送「再見」到 chat/test 並接著呼叫 chat/reset 才清空訊息', async () => {
      const calls: string[] = []
      let farewellBody: { message?: string } | null = null
      server.use(
        http.post('/api/v1/agents/:id/chat/test', async ({ request }) => {
          farewellBody = (await request.json()) as { message?: string }
          calls.push('chat/test')
          return HttpResponse.json({ success: true, data: [{ text: '##end_call##' }] })
        }),
        http.post('/api/v1/agents/:id/chat/reset', () => {
          calls.push('chat/reset')
          return HttpResponse.json({ success: true })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })
      const lenAfterSend = result.current.messages.length
      expect(lenAfterSend).toBeGreaterThan(0)
      // 重置 calls 排除 send 的 chat/test
      calls.length = 0

      await act(async () => {
        await result.current.restart()
      })

      // 驗證二段呼叫順序：先「再見」、後 reset
      expect(calls).toEqual(['chat/test', 'chat/reset'])
      expect(farewellBody).toEqual({ message: '再見' })
      expect(result.current.messages).toHaveLength(0)
      expect(result.current.restarting).toBe(false)
    })

    it('chat/test 成功但 chat/reset 失敗時保留訊息並 toast.error', async () => {
      const { toast } = await import('sonner')
      server.use(
        http.post('/api/v1/agents/:id/chat/test', () =>
          HttpResponse.json({ success: true, data: [{ text: '##end_call##' }] }),
        ),
        http.post('/api/v1/agents/:id/chat/reset', () =>
          HttpResponse.json(
            { detail: { code: 'BAD_GATEWAY', message: 'reset 失敗' } },
            { status: 502 },
          ),
        ),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })
      const lenBefore = result.current.messages.length

      await act(async () => {
        await result.current.restart()
      })

      // 任一段失敗都應保留 messages，避免「清空後 Rasa 仍卡死」的不對稱狀態
      expect(result.current.messages).toHaveLength(lenBefore)
      expect(toast.error).toHaveBeenCalled()
    })

    it('restart 失敗時保留訊息並 toast.error', async () => {
      const { toast } = await import('sonner')
      // 第一次 send 用預設 handler（成功），第二次 restart 才回 502
      let callCount = 0
      server.use(
        http.post('/api/v1/agents/:id/chat/test', () => {
          callCount += 1
          if (callCount === 1) {
            return HttpResponse.json({ success: true, data: [{ text: '測試回覆' }] })
          }
          return HttpResponse.json(
            { detail: { code: 'BAD_GATEWAY', message: 'Rasa 連線失敗' } },
            { status: 502 },
          )
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })
      const lenBefore = result.current.messages.length
      expect(lenBefore).toBeGreaterThan(0)

      await act(async () => {
        await result.current.restart()
      })

      expect(result.current.messages).toHaveLength(lenBefore)
      expect(result.current.restarting).toBe(false)
      expect(toast.error).toHaveBeenCalled()
    })

    it('restart 執行期間 restarting 為 true，完成後為 false', async () => {
      let resolveRestart!: () => void
      server.use(
        http.post('/api/v1/agents/:id/chat/test', async () => {
          await new Promise<void>((r) => {
            resolveRestart = r
          })
          return HttpResponse.json({ success: true, data: [] })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      let restartPromise!: Promise<void>
      act(() => {
        restartPromise = result.current.restart()
      })

      await waitFor(() => expect(result.current.restarting).toBe(true))

      resolveRestart()
      await act(async () => {
        await restartPromise
      })

      expect(result.current.restarting).toBe(false)
    })

    it('agentId 為 undefined 時不呼叫 chat/test', async () => {
      let called = false
      server.use(
        http.post('/api/v1/agents/:id/chat/test', () => {
          called = true
          return HttpResponse.json({ success: true, data: [] })
        }),
      )

      const { result } = renderHook(() => useChat(undefined))

      await act(async () => {
        await result.current.restart()
      })

      expect(called).toBe(false)
      expect(result.current.restarting).toBe(false)
    })
  })
})
