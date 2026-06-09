import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import * as api from '@/api/endpoints/users'
import { runWithToast } from '@/lib/runWithToast'
import type { Agent } from '@/api/types'

type RoleValue = 'editor' | 'reviewer' | 'none'

interface Props {
  user_id: string
  agent: Agent
  currentRole: RoleValue
  onChanged: () => void
}

export function AgentRoleRow({ user_id, agent, currentRole, onChanged }: Props) {
  async function handleChange(next: RoleValue) {
    const r = await runWithToast(
      () => next === 'none'
        ? api.removeRole(user_id, agent.id)
        : api.assignRole(user_id, agent.id, next),
      { success: next === 'none' ? `已移除 ${agent.name} 角色` : `已設為 ${next}` },
    )
    if (r.ok) onChanged()
  }

  return (
    <div className="flex items-center justify-between py-2 border-b border-border-default last:border-b-0">
      <span className="text-sm">{agent.name}</span>
      <Select value={currentRole} onValueChange={(v) => handleChange(v as RoleValue)}>
        <SelectTrigger className="w-32 h-8"><SelectValue /></SelectTrigger>
        <SelectContent>
          <SelectItem value="none">— 無權限</SelectItem>
          <SelectItem value="editor">Editor</SelectItem>
          <SelectItem value="reviewer">Reviewer</SelectItem>
        </SelectContent>
      </Select>
    </div>
  )
}
