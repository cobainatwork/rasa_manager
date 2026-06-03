import { useState, useRef, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import { Send, Trash2, RotateCcw } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { ScrollArea } from '@/components/ui/scroll-area'
import { useChat } from './useChat'
import { ChatBubble } from './ChatBubble'
import { TypingIndicator } from './TypingIndicator'

const SUGGESTED_PROMPTS = ['你好', '請問退費政策？', '請問今天天氣？'] as const

export function TestChatPage() {
  const { id } = useParams<{ id: string }>()
  const { messages, sending, resetting, restarting, send, clear, restart } = useChat(id)
  const [draft, setDraft] = useState('')
  const [refocusTick, setRefocusTick] = useState(0)
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

  // 在 sending 由 true → false 後（disabled 已移除）以 effect 自然觸發 focus，
  // 取代原本的 setTimeout(0) trick。refocusTick 用來在每次「送完一則」後重新觸發。
  useEffect(() => {
    if (!sending && refocusTick > 0) textareaRef.current?.focus()
  }, [sending, refocusTick])

  async function handleSend() {
    const text = draft.trim()
    if (!text || sending) return
    setDraft('')
    await send(text)
    setRefocusTick((t) => t + 1)
  }

  return (
    <div className="p-8 max-w-3xl h-full flex flex-col">
      <div className="flex justify-between items-center mb-4">
        <h1 className="text-2xl font-bold">對話測試</h1>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void restart()}
            disabled={restarting || resetting || sending}
          >
            <RotateCcw className="w-4 h-4 mr-1" strokeWidth={1.5} />
            {restarting ? '重新中...' : '重新對話'}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => void clear()}
            disabled={resetting || restarting || sending}
          >
            <Trash2 className="w-4 h-4 mr-1" strokeWidth={1.5} />
            {resetting ? '清除中...' : '清除對話'}
          </Button>
        </div>
      </div>

      <Card className="flex-1 flex flex-col overflow-hidden">
        <ScrollArea ref={scrollAreaRef} className="flex-1 p-4">
          <div className="space-y-3" role="log" aria-live="polite" aria-label="對話訊息">
            {messages.length === 0 && (
              <div className="py-8 flex flex-col items-center gap-4">
                <p className="text-center text-text-muted text-sm">輸入訊息開始測試對話...</p>
                <div
                  className="flex flex-wrap justify-center gap-2"
                  role="group"
                  aria-label="範例提示"
                >
                  {SUGGESTED_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => {
                        setDraft(prompt)
                        textareaRef.current?.focus()
                      }}
                      className="px-3 py-1.5 rounded-full bg-canvas text-text-primary border border-border-default text-sm hover:bg-subtle transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
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
