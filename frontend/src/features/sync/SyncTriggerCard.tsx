import { RefreshCw } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import type { SyncLog } from '@/api/types'

interface Props {
  triggering: boolean
  activeLog: SyncLog | null
  onTrigger: () => void
}

const STATUS_LABEL: Record<SyncLog['status'], string> = {
  pending: '等待中', running: '執行中', completed: '完成', failed: '失敗',
}

export function SyncTriggerCard({ triggering, activeLog, onTrigger }: Props) {
  const inProgress = activeLog && activeLog.status !== 'completed' && activeLog.status !== 'failed'

  return (
    <Card className="p-6">
      <h2 className="text-lg font-semibold mb-2">觸發新同步</h2>
      <p className="text-sm text-text-secondary mb-4">
        將取出狀態為「已核准」與「已同步」的 FAQ 匯出至 .txt 並執行 ingestion 腳本。
      </p>
      <Button onClick={onTrigger} disabled={triggering || !!inProgress}>
        <RefreshCw className={`w-4 h-4 mr-1 ${triggering ? 'animate-spin' : ''}`} strokeWidth={1.5} />
        {triggering ? '觸發中...' : inProgress ? `${STATUS_LABEL[activeLog!.status]}...` : '立即觸發同步'}
      </Button>

      {inProgress && (
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded animate-pulse text-sm text-blue-900">
          任務 {activeLog!.id.slice(0, 8)}... 進行中（{STATUS_LABEL[activeLog!.status]}）
        </div>
      )}
    </Card>
  )
}
