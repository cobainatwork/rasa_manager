import { useState } from 'react'
import { apiClient } from '@/api/client'
import { extractFilenameFromHeader } from '@/api/filename-utils'
import { downloadBlob } from '@/lib/download'
import { runWithToast } from '@/lib/runWithToast'

export function useExport(agentId: string | undefined) {
  const [exporting, setExporting] = useState(false)

  async function exportXlsx() {
    if (!agentId) return
    await runWithToast(
      async () => {
        const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/export`, {
          responseType: 'blob',
        })
        const disposition = resp.headers['content-disposition'] as string | undefined
        const filename = extractFilenameFromHeader(disposition, 'faq_export.xlsx')
        const blob = new Blob([resp.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        downloadBlob(blob, filename)
      },
      { success: '匯出完成', busy: setExporting },
    )
  }

  return { exporting, exportXlsx }
}
