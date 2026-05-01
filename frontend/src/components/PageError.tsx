import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useNavigate } from 'react-router-dom'
import { ROUTE_PATHS } from '@/routes/paths'

interface Props {
  message?: string
  /** I14：由 ErrorBoundary 注入的重置函式；未提供時 fallback 至整頁重整 */
  onReset?: () => void
}

export function PageError({ message, onReset }: Props) {
  const navigate = useNavigate()
  const handleReset = onReset ?? (() => location.reload())
  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-8">
      <AlertTriangle className="w-16 h-16 text-amber-500 mb-4" strokeWidth={1.5} />
      <h1 className="text-2xl font-bold mb-2">系統發生錯誤</h1>
      <p className="text-text-secondary mb-6">{message ?? '我們已記錄此問題，請稍後再試。'}</p>
      <div className="flex gap-3">
        <Button variant="outline" onClick={handleReset}>重新整理</Button>
        <Button onClick={() => navigate(ROUTE_PATHS.agents)}>回到 Dashboard</Button>
      </div>
    </div>
  )
}
