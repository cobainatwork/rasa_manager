import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import * as api from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
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
    try {
      if (next === 'none') {
        await api.removeRole(user_id, agent.id)
        toast.success(`已移除 ${agent.name} 角色`)
      } else {
        await api.assignRole(user_id, agent.id, next)
        toast.success(`已設為 ${next}`)
      }
      onChanged()
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
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
