import { useEffect, useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ShieldCheck, AlertTriangle } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { listAgents } from '@/api/endpoints/agents'
import * as userApi from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { formatDate } from '@/lib/format'
import { AgentRoleRow } from './AgentRoleRow'
import type { Agent, User } from '@/api/types'

const pwSchema = z.object({
  newPassword: z.string()
    .min(8, '至少 8 字元')
    .regex(/[A-Z]/)
    .regex(/[a-z]/)
    .regex(/\d/),
})
type PwForm = z.infer<typeof pwSchema>

interface UserAgentRoleEntry { agent_id: string; role: 'editor' | 'reviewer' }

interface Props {
  user: User
  userRoles: UserAgentRoleEntry[]
  onChanged: () => void
}

export function UserDetailPanel({ user, userRoles, onChanged }: Props) {
  const [agents, setAgents] = useState<Agent[]>([])
  const [showResetPw, setShowResetPw] = useState(false)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<PwForm>({
    resolver: zodResolver(pwSchema),
  })

  useEffect(() => {
    listAgents().then(setAgents).catch(() => setAgents([]))
  }, [])

  async function toggleActive(checked: boolean) {
    try {
      await userApi.updateUser(user.id, { is_active: checked })
      toast.success(checked ? '已啟用' : '已停用')
      onChanged()
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  async function handleResetPw(data: PwForm) {
    try {
      await userApi.resetPassword(user.id, data.newPassword)
      toast.success('密碼已重設')
      reset()
      setShowResetPw(false)
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  async function handleDelete() {
    try {
      await userApi.deleteUser(user.id)
      toast.success('使用者已刪除')
      onChanged()
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  function roleOf(agentId: string): 'editor' | 'reviewer' | 'none' {
    return userRoles.find((r) => r.agent_id === agentId)?.role ?? 'none'
  }

  return (
    <ScrollArea className="flex-1">
      <div className="p-6 space-y-6 max-w-2xl">
        <Card className="p-5 space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            {user.is_superadmin && <ShieldCheck className="w-4 h-4 text-purple-600" strokeWidth={1.5} />}
            基本資訊
          </h2>
          <Field label="帳號" value={user.username} />
          <Field label="角色" value={user.is_superadmin ? 'Superadmin' : '一般使用者'} />
          <Field label="建立時間" value={formatDate(user.created_at)} />
          <div className="flex items-center justify-between">
            <Label htmlFor="active">啟用狀態</Label>
            <Switch id="active" checked={user.is_active} onCheckedChange={toggleActive} disabled={user.is_superadmin} />
          </div>
        </Card>

        {!user.is_superadmin && (
          <Card className="p-5">
            <h2 className="font-semibold mb-3">各 Agent 角色</h2>
            {agents.length === 0 ? (
              <p className="text-sm text-text-muted">尚未建立任何 Agent</p>
            ) : (
              agents.map((a) => (
                <AgentRoleRow
                  key={a.id}
                  user_id={user.id}
                  agent={a}
                  currentRole={roleOf(a.id)}
                  onChanged={onChanged}
                />
              ))
            )}
          </Card>
        )}

        <Card className="p-5 border-red-200 border-2 space-y-3">
          <h2 className="font-semibold text-red-700 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4" strokeWidth={1.5} /> 危險區
          </h2>

          {!showResetPw ? (
            <Button variant="outline" onClick={() => setShowResetPw(true)}>重設密碼</Button>
          ) : (
            <form onSubmit={handleSubmit(handleResetPw)} className="space-y-2">
              <Label className="text-xs">新密碼</Label>
              <Input type="password" {...register('newPassword')} placeholder="至少 8 字元，含大小寫與數字" />
              {errors.newPassword && <p className="text-xs text-red-600">{errors.newPassword.message}</p>}
              <div className="flex gap-2">
                <Button type="submit" size="sm">確認</Button>
                <Button type="button" variant="outline" size="sm" onClick={() => { reset(); setShowResetPw(false) }}>取消</Button>
              </div>
            </form>
          )}

          {!user.is_superadmin && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button variant="destructive" className="w-full">刪除使用者</Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>確認刪除「{user.username}」？</AlertDialogTitle>
                  <AlertDialogDescription>此操作無法復原。</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>取消</AlertDialogCancel>
                  <AlertDialogAction onClick={handleDelete} className="bg-red-600 hover:bg-red-700">永久刪除</AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </Card>
      </div>
    </ScrollArea>
  )
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between text-sm">
      <span className="text-text-secondary">{label}</span>
      <span className="font-medium">{value}</span>
    </div>
  )
}
