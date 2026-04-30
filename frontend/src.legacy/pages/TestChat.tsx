import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import type { ChatMessage } from '@/api/types'

interface ChatBubble {
  role: 'user' | 'bot'
  text: string
}

export function TestChat() {
  const { id: agentId } = useParams<{ id: string }>()
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ChatBubble[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const send = async () => {
    if (!input.trim() || !agentId) return
    const userMsg = input.trim()
    setMessages((m) => [...m, { role: 'user', text: userMsg }])
    setInput('')
    setSending(true)
    setError(null)
    try {
      const resp = await apiClient.post(`/api/v1/agents/${agentId}/chat/test`, { message: userMsg })
      const replies: ChatMessage[] = resp.data?.data ?? []
      const botMessages: ChatBubble[] = replies
        .filter((r) => r.text)
        .map((r) => ({ role: 'bot' as const, text: r.text! }))
      setMessages((m) => [...m, ...botMessages])
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="p-8 max-w-3xl flex flex-col h-[calc(100vh-4rem)]">
      <h1 className="text-2xl font-bold mb-4">對話測試</h1>

      <div className="card flex-1 overflow-auto p-4 space-y-3 mb-4">
        {messages.length === 0 && (
          <p className="text-slate-400 text-center py-8">輸入訊息開始對話測試</p>
        )}
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={m.role === 'user' ? 'flex justify-end' : 'flex justify-start'}
          >
            <div
              className={
                m.role === 'user'
                  ? 'bg-blue-600 text-white rounded-lg px-4 py-2 max-w-[80%]'
                  : 'bg-slate-200 text-slate-900 rounded-lg px-4 py-2 max-w-[80%]'
              }
            >
              {m.text}
            </div>
          </div>
        ))}
        {sending && (
          <div className="flex justify-start">
            <div className="bg-slate-100 text-slate-500 rounded-lg px-4 py-2 text-sm animate-pulse">
              Rasa 思考中...
            </div>
          </div>
        )}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3 mb-2">
          {error}
        </div>
      )}

      <div className="flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !sending && send()}
          placeholder="輸入訊息..."
          className="input flex-1"
          disabled={sending}
        />
        <button onClick={send} disabled={sending || !input.trim()} className="btn-primary">
          送出
        </button>
      </div>
    </div>
  )
}
