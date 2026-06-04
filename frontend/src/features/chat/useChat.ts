import { useRef, useState } from 'react'
import { apiClient, extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'

export interface ChatMessage {
  id: string
  role: 'user' | 'bot'
  text: string
  /** 僅最後一則 bot 回覆攜帶：從送出請求到收到回應的毫秒數 */
  responseMs?: number
}

/** 產生 conversation sender ID — 對齊 Rasa OpenAPI custom channel webhook 的 sender 欄位。
 *  每次「重新對話」/「清除對話」換新，Rasa tracker 從乾淨狀態開始（per-session 隔離）。 */
function newSenderId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }
  // 環境無 crypto.randomUUID 時 fallback
  return `s-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

/** 解析 Rasa REST webhook 回應為 ChatMessage 陣列。
 *  回應 schema：`data` 為 `{ text?: string, image?: string, ... }[]`。
 *  僅保留含 text 的回覆；最後一則 bot 訊息掛上 responseMs。 */
function parseReplies(raw: unknown, responseMs: number): ChatMessage[] {
  const replies: { text?: string }[] = Array.isArray(raw) ? raw : []
  const filtered = replies.filter((r) => r.text)
  const ts = Date.now()
  return filtered.map((r, i) => ({
    id: `b-${ts}-${i}`,
    role: 'bot' as const,
    text: r.text!,
    ...(i === filtered.length - 1 ? { responseMs } : {}),
  }))
}

export function useChat(agentId: string | undefined) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [sending, setSending] = useState(false)
  const [resetting, setResetting] = useState(false)
  const [restarting, setRestarting] = useState(false)
  const senderRef = useRef<string>(newSenderId())

  async function send(text: string) {
    if (!agentId || !text.trim()) return
    const userMsg: ChatMessage = { id: `u-${Date.now()}`, role: 'user', text }
    setMessages((m) => [...m, userMsg])
    setSending(true)
    const startAt = Date.now()
    try {
      const resp = await apiClient.post(`/api/v1/agents/${agentId}/chat/test`, {
        sender: senderRef.current,
        message: text,
      })
      const responseMs = Date.now() - startAt
      const botMsgs = parseReplies(resp.data?.data, responseMs)
      setMessages((m) => [...m, ...botMsgs])
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  async function clear() {
    // 「清除對話」：換新 sender → Rasa 端視為全新 conversation。
    // 不再呼叫 chat/reset 端點 — 換 sender 是更乾淨的隔離方式（無網路 race / 失敗風險）。
    if (!agentId || resetting) return
    setResetting(true)
    try {
      senderRef.current = newSenderId()
      setMessages([])
    } finally {
      setResetting(false)
    }
  }

  async function restart() {
    // 「重新對話」：先用舊 sender 送「再見」讓 Rasa 跑 hangup_flow（留 audit 痕跡），
    // 再換新 sender → 下次對話從乾淨狀態開始（不再受 Rasa terminated state 影響）。
    // 送「再見」失敗則 abort（不換 sender、不清訊息）— 讓使用者知道有網路問題、重試。
    if (!agentId || restarting) return
    setRestarting(true)
    try {
      await apiClient.post(`/api/v1/agents/${agentId}/chat/test`, {
        sender: senderRef.current,
        message: '再見',
      })
      senderRef.current = newSenderId()
      setMessages([])
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setRestarting(false)
    }
  }

  return { messages, sending, resetting, restarting, send, clear, restart }
}
