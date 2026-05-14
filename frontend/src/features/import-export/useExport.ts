import { useState } from 'react'
import { apiClient, extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { extractFilenameFromHeader } from '@/api/filename-utils'
import { downloadBlob } from '@/lib/download'

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
      const blob = new Blob([resp.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      })
      downloadBlob(blob, filename)
      toast.success('匯出完成')
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  return { exporting, exportXlsx }
}
