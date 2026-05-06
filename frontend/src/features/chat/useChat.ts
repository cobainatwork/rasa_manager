import { useState } from 'react'
import { apiClient, extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'

export interface ChatMessage {
  id: string
  role: 'user' | 'bot'
  text: string
  /** 僅最後一則 bot 回覆攜帶：從送出請求到收到回應的毫秒數 */
  responseMs?: number
}

export function useChat(agentId: string | undefined) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)

  async function send(text: string) {
    if (!agentId || !text.trim()) return
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', text }
    setMessages((m) => [...m, userMsg])
    setSending(true)
    const startAt = Date.now()
    try {
      const resp = await apiClient.post(`/api/v1/agents/${agentId}/chat/test`, { message: text })
      const responseMs = Date.now() - startAt
      const raw = resp.data?.data
      // Rasa 部分自訂 connector 可能回傳 {} 或非陣列，以 Array.isArray 守衛
      const replies: { text?: string }[] = Array.isArray(raw) ? raw : []
      const filtered = replies.filter((r) => r.text)
      const botMsgs: ChatMessage[] = filtered.map((r, i) => ({
        id: `b-${Date.now()}-${i}`,
        role: 'bot' as const,
        text: r.text!,
        // 僅最後一則 bot 回覆攜帶反應時間，避免多泡泡重複顯示
        ...(i === filtered.length - 1 ? { responseMs } : {}),
      }))
      setMessages((m) => [...m, ...botMsgs])
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  function clear() { setMessages([]) }
  return { messages, sending, send, clear }
}
