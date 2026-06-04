import { RefreshCw } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { SYNC_STATUS_LABEL } from './syncStatus'
import type { SyncLog } from '@/api/types'

interface Props {
  triggering: boolean
  activeLog: SyncLog | null
  onTrigger: () => void
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
        {triggering ? '觸發中...' : inProgress ? `${SYNC_STATUS_LABEL[activeLog!.status]}...` : '立即觸發同步'}
      </Button>

      {inProgress && (
        <div className="mt-4 p-3 bg-brand-500/[0.08] border border-brand-500/[0.20] rounded-lg text-sm text-brand-700">
          任務 {activeLog!.id.slice(0, 8)}... 進行中（{SYNC_STATUS_LABEL[activeLog!.status]}）
        </div>
      )}
    </Card>
  )
}
