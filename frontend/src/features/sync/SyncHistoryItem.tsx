import { useState } from 'react'
import { ChevronRight, ChevronDown, CheckCircle2, XCircle, Loader2, Clock } from 'lucide-react'
import { cn } from '@/lib/utils'
import { relativeTime, formatDate } from '@/lib/format'
import { SYNC_STATUS_LABEL } from './syncStatus'
import type { SyncLog } from '@/api/types'
import type { SyncLogHistoryItem as Item } from '@/api/types'

const STATUS_BG: Record<SyncLog['status'], string> = {
  completed: 'bg-emerald-500/[0.06] border-emerald-500/[0.20]',
  failed:    'bg-red-500/[0.06] border-red-500/[0.20]',
  running:   'bg-brand-500/[0.06] border-brand-500/[0.20]',
  pending:   'bg-surface border-border-default',
}

function StatusIcon({ status }: { status: SyncLog['status'] }) {
  if (status === 'completed') return <CheckCircle2 className="w-4 h-4 text-emerald-600" strokeWidth={1.5} />
  if (status === 'failed')    return <XCircle      className="w-4 h-4 text-red-600"     strokeWidth={1.5} />
  if (status === 'running')   return <Loader2      className="w-4 h-4 text-brand-500 animate-spin" strokeWidth={1.5} />
  return                             <Clock        className="w-4 h-4 text-text-muted"  strokeWidth={1.5} />
}

export function SyncHistoryItem({ item }: { item: Item }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <li className={cn('border rounded-lg p-3 transition-colors', STATUS_BG[item.status])}>
      <button
        type="button"
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 text-left text-sm cursor-pointer"
      >
        {expanded
          ? <ChevronDown  className="w-4 h-4 text-text-muted shrink-0" strokeWidth={1.5} />
          : <ChevronRight className="w-4 h-4 text-text-muted shrink-0" strokeWidth={1.5} />}
        <StatusIcon status={item.status} />
        <span className="font-medium">{SYNC_STATUS_LABEL[item.status]}</span>
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
              <pre className="mt-1 p-2 bg-red-500/[0.08] text-red-800 rounded text-xs overflow-auto max-h-40 whitespace-pre-wrap">{item.stderr}</pre>
            </details>
          )}
        </div>
      )}
    </li>
  )
}
