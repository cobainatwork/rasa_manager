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
    // 「重新對話」二段：
    //   1) 送「再見」讓 Rasa 跑 hangup_flow（會回 ##end_call## 並把 conversation
    //      terminate，後續訊息會被吞掉、回 messages:[]）
    //   2) 必須緊接 PUT 空 events 強制 reset tracker，否則使用者下次對話永遠卡死
    // 為何不只 reset？保留「再見」可讓 Rasa audit / session_log 看到自然告別訊號。
    if (!agentId || restarting) return
    setRestarting(true)
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/chat/test`, { message: '再見' })
      await apiClient.post(`/api/v1/agents/${agentId}/chat/reset`)
      setMessages([])
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setRestarting(false)
    }
  }

  return { messages, sending, resetting, restarting, send, clear, restart }
}
