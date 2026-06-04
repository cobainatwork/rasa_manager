import { useState } from 'react'
import { ChevronRight, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { formatDate } from '@/lib/format'
import type { AuditLogEntry as Entry } from '@/api/types'

const ACTION_LABELS: Record<string, string> = {
  create: '建立', update: '編輯', delete: '刪除',
  submit: '送審', approve: '核准', reject: '退回', sync: '觸發同步',
}

export function AuditEntry({ entry }: { entry: Entry }) {
  const [expanded, setExpanded] = useState(false)
  const hasDiff = entry.diff && Object.keys(entry.diff).length > 0
  const date = entry.created_at ? new Date(entry.created_at) : null
  const time = date ? date.toTimeString().slice(0, 5) : '—'

  return (
    <li className="border-b border-border-default py-2">
      <button
        type="button"
        onClick={() => hasDiff && setExpanded(!expanded)}
        className={cn('w-full flex items-center gap-2 text-sm text-left rounded px-2 -mx-2 py-1 -my-1 transition-colors', hasDiff ? 'cursor-pointer hover:bg-black/[0.04]' : 'cursor-default')}
      >
        {hasDiff && (expanded ? <ChevronDown className="w-3.5 h-3.5" strokeWidth={1.5} /> : <ChevronRight className="w-3.5 h-3.5" strokeWidth={1.5} />)}
        <span className="text-text-muted font-mono text-xs w-12">{time}</span>
        <span className="font-medium">{entry.performed_by_username ?? '系統'}</span>
        <span className="text-text-secondary">{ACTION_LABELS[entry.action] ?? entry.action}</span>
      </button>

      {expanded && hasDiff && (
        <div className="mt-2 ml-7">
          <table className="w-full text-xs">
            <thead className="text-text-muted">
              <tr>
                <th className="text-left">欄位</th>
                <th className="text-left">前</th>
                <th className="text-left">後</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(entry.diff!).map(([field, change]) => (
                <tr key={field} className="border-t border-border-default">
                  <td className="py-1 font-mono">{field}</td>
                  <td className="py-1 bg-red-500/[0.08] text-red-700">{JSON.stringify(change.before)}</td>
                  <td className="py-1 bg-emerald-500/[0.08] text-emerald-700">{JSON.stringify(change.after)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div className="ml-7 text-xs text-text-muted">{formatDate(entry.created_at)}</div>
    </li>
  )
}
