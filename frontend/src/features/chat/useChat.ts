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
  const [resetting, setResetting] = useState(false)
  const [restarting, setRestarting] = useState(false)

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

  async function clear() {
    // 「清除對話」不只清前端 state，還要同步 reset Rasa conversation tracker，
    // 避免 Rasa Pro flow 卡在某個 slot 後續訊息全被吞掉。
    if (!agentId || resetting) return
    setResetting(true)
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/chat/reset`)
      setMessages([])
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setResetting(false)
    }
  }

  async function restart() {
    // 「重新對話」走 Rasa 自然告別 flow：送「再見」讓 Rasa 自行結束 session，
    // 再清前端訊息。比 clear() 軟性，依賴 Rasa flows 設計能否觸發 hangup_flow。
    if (!agentId || restarting) return
    setRestarting(true)
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/chat/test`, { message: '再見' })
      setMessages([])
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setRestarting(false)
    }
  }

  return { messages, sending, resetting, restarting, send, clear, restart }
}
