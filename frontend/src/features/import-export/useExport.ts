import { useState } from 'react'
import { apiClient, extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'

export function useExport(agentId: string | undefined) {
  const [exporting, setExporting] = useState(false)

  async function exportXlsx() {
    if (!agentId) return
    setExporting(true)
    try {
      const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/export`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(new Blob([resp.data], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      }))
      const a = document.createElement('a')
      a.href = url
      a.download = 'faq_export.xlsx'
      a.click()
      URL.revokeObjectURL(url)
      toast.success('匯出完成')
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setExporting(false)
    }
  }

  return { exporting, exportXlsx }
}
