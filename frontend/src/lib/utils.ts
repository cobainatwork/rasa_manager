import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs))
}

export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '-'
  const d = new Date(iso)
  return d.toLocaleString('zh-TW', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  pending: '待審核',
  approved: '已核准',
  rejected: '已退回',
  synced: '已同步',
}

export const ACTION_LABELS: Record<string, string> = {
  create: '建立',
  update: '修改',
  delete: '刪除',
  approve: '核准',
  reject: '退回',
  approved: '核准',
  rejected: '退回',
  pending: '送審',
  draft: '撤回/降級',
  synced: '同步完成',
  rollback: '版本還原',
  edited: '編輯',
  created: '建立',
  export: '匯出',
  import: '匯入',
}
