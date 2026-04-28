import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { useAuthStore } from '@/store/useAuthStore'
import { extractErrorMessage } from '@/api/client'

const schema = z.object({
  username: z.string().min(1, '請輸入帳號'),
  password: z.string().min(1, '請輸入密碼'),
})

type FormData = z.infer<typeof schema>

export function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuthStore((s) => s.login)
  const [serverError, setServerError] = useState<string | null>(null)

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setServerError(null)
    try {
      await login(data.username, data.password)
      const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/agents'
      navigate(from, { replace: true })
    } catch (err) {
      setServerError(extractErrorMessage(err))
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 p-4">
      <div className="card p-8 w-full max-w-md">
        <h1 className="text-2xl font-bold text-center mb-2">Rasa 知識庫管理平台</h1>
        <p className="text-center text-slate-500 text-sm mb-6">請輸入您的帳號與密碼</p>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="label">帳號</label>
            <input className="input" {...register('username')} autoComplete="username" />
            {errors.username && <p className="text-red-600 text-xs mt-1">{errors.username.message}</p>}
          </div>

          <div>
            <label className="label">密碼</label>
            <input type="password" className="input" {...register('password')} autoComplete="current-password" />
            {errors.password && <p className="text-red-600 text-xs mt-1">{errors.password.message}</p>}
          </div>

          {serverError && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-md p-3">
              {serverError}
            </div>
          )}

          <button type="submit" disabled={isSubmitting} className="btn-primary w-full">
            {isSubmitting ? '登入中...' : '登入'}
          </button>
        </form>
      </div>
    </div>
  )
}
