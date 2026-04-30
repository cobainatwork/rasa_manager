import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { AlertTriangle } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
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
import * as userApi from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { User } from '@/api/types'

const pwSchema = z.object({
  newPassword: z.string()
    .min(8, '至少 8 字元')
    .regex(/[A-Z]/)
    .regex(/[a-z]/)
    .regex(/\d/),
})
type PwForm = z.infer<typeof pwSchema>

interface Props {
  user: User
  onChanged: () => void
}

export function UserDangerZone({ user, onChanged }: Props) {
  const [showResetPw, setShowResetPw] = useState(false)
  const { register, handleSubmit, reset, formState: { errors } } = useForm<PwForm>({
    resolver: zodResolver(pwSchema),
  })

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

  return (
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
  )
}
