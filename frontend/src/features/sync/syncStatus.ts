import type { SyncLog } from '@/api/types'

export const SYNC_STATUS_LABEL: Record<SyncLog['status'], string> = {
  pending: '等待中',
  running: '執行中',
  completed: '完成',
  failed: '失敗',
}
