import { useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import { apiClient, extractErrorMessage } from '@/api/client'
import { useToastStore } from '@/store/useToastStore'

interface ImportResult {
  imported: number
  skipped: number
  errors: { row: number; reason: string }[]
  new_categories: string[]
}

export function ImportExport() {
  const { id: agentId } = useParams<{ id: string }>()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { addToast } = useToastStore()

  const [importing, setImporting] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [importResult, setImportResult] = useState<ImportResult | null>(null)
  const [importError, setImportError] = useState<string | null>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null
    setSelectedFile(f)
    setImportResult(null)
    setImportError(null)
  }

  const handleImport = async () => {
    if (!selectedFile || !agentId) return
    setImporting(true)
    setImportResult(null)
    setImportError(null)

    const form = new FormData()
    form.append('file', selectedFile)

    try {
      const resp = await apiClient.post(
        `/api/v1/agents/${agentId}/faqs/import`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      setImportResult(resp.data?.data ?? null)
    } catch (err) {
      setImportError(extractErrorMessage(err))
    } finally {
      setImporting(false)
      // 清空 input
      if (fileInputRef.current) fileInputRef.current.value = ''
      setSelectedFile(null)
    }
  }

  const handleExport = async () => {
    if (!agentId) return
    setExporting(true)
    try {
      const resp = await apiClient.get(`/api/v1/agents/${agentId}/faqs/export`, {
        responseType: 'blob',
      })
      const url = URL.createObjectURL(
        new Blob([resp.data], {
          type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        }),
      )
      const a = document.createElement('a')
      a.href = url
      a.download = 'faq_export.xlsx'
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      addToast(extractErrorMessage(err), 'error')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="p-8 max-w-3xl space-y-8">
      <h1 className="text-2xl font-bold">匯入 / 匯出</h1>

      {/* ── 匯入區塊 ── */}
      <div className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold">批次匯入 FAQ</h2>
        <p className="text-sm text-slate-500">
          上傳 <code className="bg-slate-100 px-1 rounded">.xlsx</code> 檔案，必填欄位：
          <code className="bg-slate-100 px-1 rounded mx-1">question</code>、
          <code className="bg-slate-100 px-1 rounded mx-1">answer</code>、
          <code className="bg-slate-100 px-1 rounded mx-1">category_path</code>（以 <code>/</code> 分隔）。
          選填欄位：<code className="bg-slate-100 px-1 rounded mx-1">tags</code>（逗號分隔）。
          匯入後一律為 <span className="badge bg-slate-200 text-slate-700">draft</span> 狀態。
          上限：10 MB / 5000 行。
        </p>

        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx"
            onChange={handleFileChange}
            className="text-sm text-slate-600 file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <button
            onClick={handleImport}
            disabled={!selectedFile || importing}
            className="btn-primary disabled:opacity-50"
          >
            {importing ? '匯入中...' : '開始匯入'}
          </button>
        </div>

        {importError && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3">
            {importError}
          </div>
        )}

        {importResult && (
          <div className="space-y-3">
            {/* 統計 */}
            <div className="flex gap-4 text-sm">
              <span className="text-green-700 font-medium">成功匯入：{importResult.imported} 筆</span>
              <span className="text-amber-700 font-medium">跳過（重複）：{importResult.skipped} 筆</span>
              <span className="text-red-700 font-medium">錯誤：{importResult.errors.length} 筆</span>
            </div>

            {/* 新建分類提示 */}
            {importResult.new_categories.length > 0 && (
              <div className="bg-blue-50 border border-blue-200 text-blue-800 text-sm rounded p-3">
                <p className="font-medium mb-1">自動建立新分類：</p>
                <ul className="list-disc list-inside space-y-0.5">
                  {importResult.new_categories.map((c) => (
                    <li key={c}>{c}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* 錯誤列表 */}
            {importResult.errors.length > 0 && (
              <div className="bg-red-50 border border-red-200 rounded p-3">
                <p className="text-sm font-medium text-red-700 mb-2">錯誤明細：</p>
                <table className="w-full text-xs text-red-800">
                  <thead>
                    <tr>
                      <th className="text-left w-16 pb-1">列號</th>
                      <th className="text-left pb-1">原因</th>
                    </tr>
                  </thead>
                  <tbody>
                    {importResult.errors.map((e, i) => (
                      <tr key={i} className="border-t border-red-100">
                        <td className="py-0.5">{e.row}</td>
                        <td className="py-0.5">{e.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </div>

      {/* ── 匯出區塊 ── */}
      <div className="card p-6 space-y-4">
        <h2 className="text-lg font-semibold">匯出所有 FAQ</h2>
        <p className="text-sm text-slate-500">
          將此 Agent 下全部 FAQ（含各狀態）匯出為
          <code className="bg-slate-100 px-1 rounded mx-1">faq_export.xlsx</code>。
          欄位：id、status、category_path、tags、question、answer、version、created_at、updated_at。
        </p>
        <button
          onClick={handleExport}
          disabled={exporting}
          className="btn-primary disabled:opacity-50"
        >
          {exporting ? '匯出中...' : '下載 Excel'}
        </button>
      </div>
    </div>
  )
}
