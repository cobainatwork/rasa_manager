import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import * as api from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { useAuthStore } from '@/store/useAuthStore'
import type { Faq } from '@/api/types'

interface Props {
  agentId: string
  faq: Faq
  onChanged: () => void
  onDeleted?: () => void
}

export function StatusActions({ agentId, faq, onChanged, onDeleted }: Props) {
  const isSuper = useAuthStore((s) => s.user?.is_superadmin ?? false)
  const [rejectReason, setRejectReason] = useState('')
  const [busy, setBusy] = useState(false)

  async function call(fn: () => Promise<unknown>, success: string, onSuccess?: () => void) {
    setBusy(true)
    try { await fn(); toast.success(success); (onSuccess ?? onChanged)() }
    catch (err) { toast.error(extractErrorMessage(err)) }
    finally { setBusy(false) }
  }

  return (
    <div className="flex flex-wrap gap-2 pt-3 border-t border-border-default">
      {(faq.status === 'draft' || faq.status === 'rejected') && (
        <Button disabled={busy} onClick={() => call(() => api.submit(agentId, faq.id), '已送審')}>送審</Button>
      )}
      {faq.status === 'pending' && (
        <>
          <Button disabled={busy} onClick={() => call(() => api.approve(agentId, faq.id), '已核准')}>核准</Button>
          <AlertDialog>
            <AlertDialogTrigger asChild>
              <Button variant="outline" disabled={busy}>退回</Button>
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>退回此 FAQ？</AlertDialogTitle>
                <AlertDialogDescription>請填寫退回理由（必填）。</AlertDialogDescription>
              </AlertDialogHeader>
              <Textarea value={rejectReason} onChange={(e) => setRejectReason(e.target.value)} placeholder="退回理由..." />
              <AlertDialogFooter>
                <AlertDialogCancel>取消</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => {
                    if (!rejectReason.trim()) { toast.error('請填寫退回理由'); return }
                    call(() => api.reject(agentId, faq.id, rejectReason), '已退回')
                    setRejectReason('')
                  }}
                >
                  確認退回
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </>
      )}
      {faq.status === 'approved' && isSuper && (
        <Button variant="outline" disabled={busy} onClick={() => call(() => api.unapprove(agentId, faq.id), '已取消核准')}>取消核准</Button>
      )}

      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button variant="destructive" disabled={busy} className="ml-auto">刪除</Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>確認刪除？</AlertDialogTitle>
            <AlertDialogDescription>將同時清除版本歷史，無法復原。</AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700"
              onClick={() => call(() => api.deleteFaq(agentId, faq.id), '已刪除', onDeleted)}
            >
              永久刪除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
