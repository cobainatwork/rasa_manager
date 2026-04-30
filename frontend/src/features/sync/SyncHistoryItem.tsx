import { useState } from 'react'
import { ChevronRight, ChevronDown, CheckCircle2, XCircle } from 'lucide-react'
import { cn } from '@/lib/utils'
import { relativeTime, formatDate } from '@/lib/format'
import type { SyncLogHistoryItem as Item } from '@/api/types'

export function SyncHistoryItem({ item }: { item: Item }) {
  const [expanded, setExpanded] = useState(false)
  const isOk = item.status === 'completed'
  const Icon = isOk ? CheckCircle2 : XCircle

  return (
    <li className={cn('border border-border-default rounded p-3', isOk ? 'bg-emerald-50' : item.status === 'failed' ? 'bg-red-50' : 'bg-surface')}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 text-left text-sm"
      >
        {expanded ? <ChevronDown className="w-4 h-4" strokeWidth={1.5} /> : <ChevronRight className="w-4 h-4" strokeWidth={1.5} />}
        <Icon className={cn('w-4 h-4', isOk ? 'text-emerald-600' : 'text-red-600')} strokeWidth={1.5} />
        <span className="font-medium">{item.status}</span>
        <span className="text-text-muted">{item.triggered_by_username ?? '系統'}</span>
        <span className="text-text-muted ml-auto">{relativeTime(item.started_at)}</span>
        <span className="text-text-muted">{item.duration_sec != null ? `${item.duration_sec}s` : '—'}</span>
        <span className="text-text-muted">{item.items_count} 筆</span>
      </button>

      {expanded && (
        <div className="mt-3 pl-7 space-y-2 text-xs">
          <div><span className="text-text-muted">開始：</span>{formatDate(item.started_at)}</div>
          <div><span className="text-text-muted">完成：</span>{formatDate(item.finished_at)}</div>
          {item.output_file && <div><span className="text-text-muted">輸出：</span><code className="bg-subtle px-1 rounded">{item.output_file}</code></div>}
          {item.stdout && (
            <details>
              <summary className="cursor-pointer text-text-muted">stdout</summary>
              <pre className="mt-1 p-2 bg-slate-900 text-slate-100 rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">{item.stdout}</pre>
            </details>
          )}
          {item.stderr && (
            <details>
              <summary className="cursor-pointer text-red-700">stderr</summary>
              <pre className="mt-1 p-2 bg-red-50 text-red-900 rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">{item.stderr}</pre>
            </details>
          )}
        </div>
      )}
    </li>
  )
}
