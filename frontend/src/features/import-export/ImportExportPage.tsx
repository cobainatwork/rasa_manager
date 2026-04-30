import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Download } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { ImportDropzone } from './ImportDropzone'
import { ImportResult } from './ImportResult'
import { useExport } from './useExport'
import { apiClient, extractErrorMessage } from '@/api/client'

interface ImportResultData {
  imported: number
  skipped: number
  errors: { row: number; reason: string }[]
  new_categories: string[]
}

export function ImportExportPage() {
  const { id } = useParams<{ id: string }>()
  const [file, setFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)
  const [progress, setProgress] = useState(0)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ImportResultData | null>(null)
  const { exporting, exportXlsx } = useExport(id)

  async function handleImport() {
    if (!file || !id) return
    setImporting(true)
    setError(null)
    setResult(null)
    setProgress(20)
    const form = new FormData()
    form.append('file', file)
    try {
      setProgress(50)
      const resp = await apiClient.post(`/api/v1/agents/${id}/faqs/import`, form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      setProgress(100)
      setResult(resp.data?.data ?? null)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setImporting(false)
      setFile(null)
    }
  }

  return (
    <div className="p-8 max-w-5xl space-y-6">
      <h1 className="text-2xl font-bold">匯入 / 匯出</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold">匯入 FAQ</h2>
          <ImportDropzone onFileSelected={setFile} selectedFile={file} />
          <p className="text-xs text-text-muted">必填欄位：question / answer / category_path（用 / 分隔）。匯入後一律為 draft 狀態。</p>
          {importing && <Progress value={progress} />}
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
          <Button onClick={handleImport} disabled={!file || importing} className="w-full">
            {importing ? '匯入中...' : '開始匯入'}
          </Button>
        </Card>

        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold">匯出 FAQ</h2>
          <p className="text-sm text-text-secondary">將此 Agent 下所有 FAQ（含各狀態）匯出為 xlsx。</p>
          <p className="text-xs text-text-muted">欄位：id / status / category_path / tags / question / answer / version / created_at / updated_at</p>
          <Button onClick={exportXlsx} disabled={exporting} className="w-full">
            <Download className="w-4 h-4 mr-1" strokeWidth={1.5} />
            {exporting ? '匯出中...' : '下載 faq_export.xlsx'}
          </Button>
        </Card>
      </div>

      {result && <ImportResult result={result} />}
    </div>
  )
}
