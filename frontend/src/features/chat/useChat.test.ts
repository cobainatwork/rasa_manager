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
    it('清空訊息並換新 sender — 下次 send 應帶新 sender', async () => {
      // 攔截兩次 send 的 sender 值
      const senders: string[] = []
      server.use(
        http.post('/api/v1/agents/:id/chat/test', async ({ request }) => {
          const body = (await request.json()) as { sender?: string }
          if (body.sender) senders.push(body.sender)
          return HttpResponse.json({ success: true, data: [{ text: 'ok' }] })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('第一句')
      })
      expect(result.current.messages.length).toBeGreaterThan(0)
      const senderBefore = senders[0]

      await act(async () => {
        await result.current.clear()
      })

      expect(result.current.messages).toHaveLength(0)
      expect(result.current.resetting).toBe(false)

      // clear 後再 send 應使用新 sender
      await act(async () => {
        await result.current.send('第二句')
      })
      const senderAfter = senders[1]
      expect(senderBefore).toBeTruthy()
      expect(senderAfter).toBeTruthy()
      expect(senderAfter).not.toEqual(senderBefore)
    })

    it('clear 不打任何 chat/reset 端點（per-session sender 是隔離正解）', async () => {
      let resetCalled = false
      server.use(
        http.post('/api/v1/agents/:id/chat/reset', () => {
          resetCalled = true
          return HttpResponse.json({ success: true })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))
      await act(async () => {
        await result.current.send('你好')
      })

      await act(async () => {
        await result.current.clear()
      })

      expect(resetCalled).toBe(false)
    })

    it('agentId 為 undefined 時 clear 不改 sender 不清訊息', async () => {
      const { result } = renderHook(() => useChat(undefined))

      await act(async () => {
        await result.current.clear()
      })

      expect(result.current.resetting).toBe(false)
    })
  })

  describe('restart', () => {
    it('用舊 sender 送「再見」，然後換新 sender 並清空訊息', async () => {
      const requests: { sender?: string; message?: string }[] = []
      server.use(
        http.post('/api/v1/agents/:id/chat/test', async ({ request }) => {
          requests.push((await request.json()) as { sender?: string; message?: string })
          return HttpResponse.json({ success: true, data: [{ text: '##end_call##' }] })
        }),
      )

      const { result } = renderHook(() => useChat(AGENT_ID))

      await act(async () => {
        await result.current.send('你好')
      })
      const senderBefore = requests[0].sender
      expect(senderBefore).toBeTruthy()
      expect(result.current.messages.length).toBeGreaterThan(0)

      await act(async () => {
        await result.current.restart()
      })

      // 第二筆（restart 內送的「再見」）應用舊 sender
      const farewellReq = requests[1]
      expect(farewellReq.sender).toEqual(senderBefore)
      expect(farewellReq.message).toEqual('再見')
      expect(result.current.messages).toHaveLength(0)
      expect(result.current.restarting).toBe(false)

      // restart 後再 send 應用「新」 sender（與 senderBefore 不同）
      await act(async () => {
        await result.current.send('再對話')
      })
      const senderAfter = requests[2].sender
      expect(senderAfter).toBeTruthy()
      expect(senderAfter).not.toEqual(senderBefore)
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
