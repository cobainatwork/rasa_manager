import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import * as api from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'

const schema = z.object({
  username: z.string().min(1, '必填').max(100),
  password: z.string()
    .min(8, '至少 8 字元')
    .regex(/[A-Z]/, '需含大寫字母')
    .regex(/[a-z]/, '需含小寫字母')
    .regex(/\d/, '需含數字'),
})
type FormData = z.infer<typeof schema>

interface Props {
  onCreated: () => void
  onCancel: () => void
}

export function AddUserInlineForm({ onCreated, onCancel }: Props) {
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    setError(null)
    try {
      await api.createUser(data)
      toast.success('使用者已建立')
      onCreated()
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  return (
    <Card className="p-4 mb-3 border-brand-500 border-2">
      <h3 className="font-semibold mb-3 text-sm">新增使用者</h3>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-3">
        <div className="space-y-1.5">
          <Label className="text-xs">帳號</Label>
          <Input {...register('username')} placeholder="username" />
          {errors.username && <p className="text-xs text-red-600">{errors.username.message}</p>}
        </div>
        <div className="space-y-1.5">
          <Label className="text-xs">密碼</Label>
          <Input type="password" {...register('password')} placeholder="至少 8 字元，含大小寫與數字" />
          {errors.password && <p className="text-xs text-red-600">{errors.password.message}</p>}
        </div>
        {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="outline" size="sm" onClick={onCancel}>取消</Button>
          <Button type="submit" size="sm" disabled={isSubmitting}>建立</Button>
        </div>
      </form>
    </Card>
  )
}
