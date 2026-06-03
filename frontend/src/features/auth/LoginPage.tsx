import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { PasswordInput } from './PasswordInput'
import { useLogin } from './useLogin'

const schema = z.object({
  username: z.string().min(1, '請輸入帳號'),
  password: z.string().min(1, '請輸入密碼'),
})

type FormData = z.infer<typeof schema>

export function LoginPage() {
  const { submit, isSubmitting, error } = useLogin()
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: FormData) => submit(data.username, data.password)

  return (
    <div className="min-h-screen flex bg-canvas">
      {/* 左側品牌區（< 1024px 隱藏） */}
      <aside className="hidden lg:flex flex-col justify-center w-3/5 bg-gradient-to-br from-brand-500 to-brand-700 text-white p-16">
        <div className="max-w-md">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-12 h-12 rounded-lg bg-white/20 backdrop-blur flex items-center justify-center font-bold text-2xl">R</div>
            <h1 className="text-3xl font-bold">Rasa 知識庫管理平台</h1>
          </div>
          <p className="text-lg text-white/90 mb-12">集中管理多 Agent 的 FAQ 與分類，一鍵同步至 Rasa。</p>
          <ul className="space-y-3 text-white">
            <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 rounded-full bg-white/80" />多 Agent 隔離管理</li>
            <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 rounded-full bg-white/80" />FAQ 版本歷史與比對</li>
            <li className="flex items-center gap-3"><span className="w-1.5 h-1.5 rounded-full bg-white/80" />一鍵同步至 Rasa REST</li>
          </ul>
        </div>
      </aside>

      {/* 右側登入表單 */}
      <main className="flex-1 flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-3 mb-8">
            <div className="w-10 h-10 rounded-lg bg-brand-500 flex items-center justify-center font-bold text-white">R</div>
            <span className="text-xl font-semibold">Rasa KB</span>
          </div>

          <h2 className="text-2xl font-bold mb-2">歡迎回來</h2>
          <p className="text-sm text-text-secondary mb-8">請輸入您的帳號與密碼</p>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
            <div className="space-y-1.5">
              <Label htmlFor="username">帳號</Label>
              <Input
                id="username"
                autoComplete="username"
                autoFocus
                aria-invalid={errors.username ? true : undefined}
                aria-describedby={errors.username ? 'username-error' : undefined}
                {...register('username')}
              />
              {errors.username && (
                <p id="username-error" role="alert" className="text-xs text-red-600">
                  {errors.username.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="password">密碼</Label>
              <PasswordInput
                id="password"
                autoComplete="current-password"
                aria-invalid={errors.password ? true : undefined}
                aria-describedby={errors.password ? 'password-error' : undefined}
                {...register('password')}
              />
              {errors.password && (
                <p id="password-error" role="alert" className="text-xs text-red-600">
                  {errors.password.message}
                </p>
              )}
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" disabled={isSubmitting} className="w-full">
              {isSubmitting ? '登入中...' : '登入'}
            </Button>
          </form>
        </div>
      </main>
    </div>
  )
}
