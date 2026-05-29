import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Send, Trash2 } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useChat } from './useChat'
import { ChatBubble } from './ChatBubble'
import { TypingIndicator } from './TypingIndicator'

export function TestChatPage() {
  const { id } = useParams<{ id: string }>()
  const { messages, sending, resetting, send, clear } = useChat(id)
  const [draft, setDraft] = useState('')
  // scrollAreaRef 指向 Radix ScrollArea 根元素，用於直接捲動 Viewport
  // 不用 scrollIntoView，避免捲動事件冒泡至 main.overflow-auto
  const scrollAreaRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector<HTMLElement>(
      '[data-radix-scroll-area-viewport]',
    )
    if (viewport) viewport.scrollTop = viewport.scrollHeight
  }, [messages, sending])

  async function handleSend() {
    const text = draft.trim()
    if (!text || sending) return
    setDraft('')
    await send(text)
    // React 18 自動批次：setSending(false) 尚未 commit 到 DOM，
    // disabled={sending} 仍為 true，直接 focus() 無效。
    // setTimeout(0) 延至下一個 macrotask，確保 disabled 已移除後再 focus。
    setTimeout(() => textareaRef.current?.focus(), 0)
  }

  return (
    <div className="p-8 max-w-3xl h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">對話測試</h1>
        <Button
          variant="outline"
          size="sm"
          onClick={() => void clear()}
          disabled={resetting || sending}
        >
          <Trash2 className="w-4 h-4 mr-1" strokeWidth={1.5} />
          {resetting ? '清除中...' : '清除對話'}
        </Button>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
          <div className="space-y-3">
            {messages.length === 0 && (
              <p className="text-center text-text-muted text-sm py-8">輸入訊息開始測試對話...</p>
            )}
            {messages.map((m) => <ChatBubble key={m.id} message={m} />)}
            {sending && <TypingIndicator />}
          </div>
        </ScrollArea>

        <div className="border-t border-border-default p-3 flex gap-2">
          <Textarea
            ref={textareaRef}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') { e.preventDefault(); void handleSend() }
            }}
            placeholder="輸入訊息（Cmd/Ctrl+Enter 送出）"
            className="flex-1 resize-none"
            rows={2}
            disabled={sending}
          />
          <Button onClick={() => void handleSend()} disabled={sending || !draft.trim()}>
            <Send className="w-4 h-4" strokeWidth={1.5} />
          </Button>
        </div>
      </Card>
    </div>
  )
}
