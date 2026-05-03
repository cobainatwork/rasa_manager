import type { AuditLogEntry } from '@/api/types'
import { AuditEntry } from './AuditEntry'

interface Props {
  date: string
  entries: AuditLogEntry[]
}

export function AuditDayGroup({ date, entries }: Props) {
  return (
    <section>
      <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wide mb-1 mt-4">{date}</h3>
      <ul>
        {entries.map((e) => <AuditEntry key={e.id} entry={e} />)}
      </ul>
    </section>
  )
}
