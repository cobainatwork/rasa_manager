/**
 * FAQ 狀態的共用常數：標籤文字與 badge 樣式 class。
 * 由 FaqListRow / FaqDetail 等元件共用，避免重複定義導致不一致。
 */
import type { Faq } from '@/api/types'

export const FAQ_STATUS_LABEL: Record<Faq['status'], string> = {
  draft: '草稿',
  pending: '待審核',
  approved: '已核准',
  rejected: '已退回',
  synced: '已同步',
}

export const FAQ_STATUS_BADGE_CLASS: Record<Faq['status'], string> = {
  draft: 'bg-slate-100 text-slate-700',
  pending: 'bg-amber-100 text-amber-800',
  approved: 'bg-emerald-100 text-emerald-800',
  rejected: 'bg-red-100 text-red-800',
  synced: 'bg-blue-100 text-blue-800',
}
