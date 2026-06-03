import { Copy } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { toast } from 'sonner'
import type { ChatMessage } from './useChat'

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  function copy() {
    navigator.clipboard.writeText(message.text)
    toast.success('已複製')
  }

  return (
    <div className={cn('flex flex-col group', isUser ? 'items-end' : 'items-start')}>
      <div className={cn('flex w-full', isUser ? 'justify-end' : 'justify-start')}>
        {!isUser && (
          <div className={cn(
            'max-w-[70%] px-4 py-2 rounded-2xl text-sm',
            'bg-subtle text-text-primary'
          )}>
            <p className="whitespace-pre-wrap">{message.text}</p>
          </div>
        )}
        {!isUser && (
          <Button variant="ghost" size="icon" onClick={copy} className="md:opacity-0 md:group-hover:opacity-100 ml-1 self-end" aria-label="複製">
            <Copy className="w-3.5 h-3.5" strokeWidth={1.5} />
          </Button>
        )}
        {isUser && (
          <div className={cn(
            'max-w-[70%] px-4 py-2 rounded-2xl text-sm',
            'bg-brand-500 text-white'
          )}>
            <p className="whitespace-pre-wrap">{message.text}</p>
          </div>
        )}
      </div>
      {message.responseMs !== undefined && (
        <span className="mt-1 text-[11px] text-text-muted select-none">
          回應 {message.responseMs.toLocaleString()} ms
        </span>
      )}
    </div>
  )
}
