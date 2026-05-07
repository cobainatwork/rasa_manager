import { useState } from 'react'
import { apiClient, extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { extractFilenameFromHeader } from '@/api/filename-utils'

export function useExport(agentId: string | undefined) {
  const [exporting, setExporting] = useState(false)

  async function exportXlsx() {
    if (!agentId) return
    setExporting(true)
    try {
      const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/export`, {
        responseType: 'blob',
      })
      const disposition = resp.headers['content-disposition'] as string | undefined
      const filename = extractFilenameFromHeader(disposition, 'faq_export.xlsx')
      const url = URL.createObjectURL(new Blob([resp.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      }))
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      a.click()
      // 延遲 revoke：瀏覽器非同步處理下載，同步 revoke 會導致 URL 在下載前失效
      setTimeout(() => URL.revokeObjectURL(url), 100)
      toast.success('匯出完成')
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  return { exporting, exportXlsx }
}
