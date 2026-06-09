import { toast } from 'sonner'
import { extractErrorMessage } from '@/api/client'

export interface RunWithToastOptions<T = unknown> {
  /** 成功時顯示的 toast 文字。未提供則不顯示 success toast */
  success?: string
  /** 任務開始/結束時呼叫的 setBusy(true|false)。會在 finally 內復位 */
  busy?: (b: boolean) => void
  /** 額外錯誤處理。toast.error 一定會呼叫，這裡是補充（例如記錄、resetForm） */
  onError?: (err: unknown) => void
  /** 成功（fn resolved）時呼叫，可拿到結果。回傳 promise 會被 await，但即使這裡 throw 也只走 onError */
  onSuccess?: (result: T) => void | Promise<void>
  /** 自訂錯誤訊息提取（預設用 extractErrorMessage） */
  formatError?: (err: unknown) => string
}

/**
 * 統一封裝「busy(true) → try { run + success toast } catch { error toast } finally { busy(false) }」樣板。
 *
 * 回傳 fn 的結果；失敗時回傳 undefined（不拋出，由 toast 顯示錯誤）。
 *
 * 注意：
 * - 不吞 SystemExit / KeyboardInterrupt — 此處為 browser JS 環境，僅捕獲一般 Error / Promise rejection。
 * - 透過 fn 拋出的非 Error 物件也會被 catch（與既有 axios error 一致）。
 *
 * 用法：
 * ```ts
 * await runWithToast(() => userApi.deleteUser(id), {
 *   success: '使用者已刪除',
 *   onError: () => closeDialog(),
 * })
 *
 * await runWithToast(() => exportXlsx(agentId), {
 *   success: '匯出完成',
 *   busy: setExporting,
 * })
 * ```
 */
export async function runWithToast<T>(
  fn: () => Promise<T>,
  opts: RunWithToastOptions<T> = {},
): Promise<{ ok: true; result: T } | { ok: false; error: unknown }> {
  const { success, busy, onError, onSuccess, formatError = extractErrorMessage } = opts
  busy?.(true)
  try {
    const result = await fn()
    if (success) toast.success(success)
    if (onSuccess) {
      try { await onSuccess(result) } catch (err) {
        // onSuccess 內若拋錯，仍走 error 流程（避免靜默失敗）
        toast.error(formatError(err))
        onError?.(err)
        return { ok: false, error: err }
      }
    }
    return { ok: true, result }
  } catch (err) {
    toast.error(formatError(err))
    onError?.(err)
    return { ok: false, error: err }
  } finally {
    busy?.(false)
  }
}
