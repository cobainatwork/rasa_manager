import { Database, Clock, RefreshCw } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { useAgentStats } from './useAgentStats'
import { relativeTime } from '@/lib/format'
import type { Agent } from '@/api/types'

interface AgentCardProps {
  agent: Agent
  onClick: (a: Agent) => void
}

export function AgentCard({ agent, onClick }: AgentCardProps) {
  const { stats } = useAgentStats(agent.id)

  return (
    <Card
      onClick={() => onClick(agent)}
      className="p-6 cursor-pointer hover:shadow-md transition-shadow duration-fast"
    >
      <h3 className="text-lg font-semibold mb-4 truncate">{agent.name}</h3>
      <div className="space-y-2 text-sm">
        <Stat icon={Database} label="FAQ 總數" value={stats?.total_faqs ?? '—'} />
        <Stat
          icon={Clock}
          label="待審核"
          value={stats?.pending_count ?? '—'}
          highlight={!!stats && stats.pending_count > 0}
        />
        <Stat icon={RefreshCw} label="最後同步" value={relativeTime(agent.created_at)} />
      </div>
      <div className="mt-4 pt-3 border-t border-border-default flex items-center gap-2">
        <Badge variant="secondary">當前角色</Badge>
        <span className="text-xs text-text-muted">點擊進入</span>
      </div>
    </Card>
  )
}

function Stat({ icon: Icon, label, value, highlight }: {
  icon: typeof Database
  label: string
  value: string | number
  highlight?: boolean
}) {
  return (
    <div className="flex items-center gap-2">
      <Icon className="w-4 h-4 text-text-muted" strokeWidth={1.5} />
      <span className="text-text-secondary">{label}：</span>
      <span className={highlight ? 'text-amber-700 font-medium' : 'text-text-primary'}>{value}</span>
    </div>
  )
}
