import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Download, AlertTriangle } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { ImportDropzone } from './ImportDropzone'
import { ImportResult } from './ImportResult'
import { useExport } from './useExport'
import { apiClient, extractErrorMessage } from '@/api/client'

type ImportMode = 'append' | 'replace'

interface ImportResultData {
  imported: number
  skipped: number
  errors: { row: number; reason: string }[]
  new_categories: string[]
}

export function ImportExportPage() {
  const { id } = useParams<{ id: string }>()
  const [file, setFile] = useState<File | null>(null)
  const [mode, setMode] = useState<ImportMode>('append')
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
      const resp = await apiClient.post(
        `/api/v1/agents/${id}/faqs/import?mode=${mode}`,
        form,
        { headers: { 'Content-Type': 'multipart/form-data' } },
      )
      setProgress(100)
      setResult(resp.data?.data ?? null)
      setTimeout(() => setProgress(0), 1200)
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

          {/* 匯入模式選擇 */}
          <div className="space-y-2">
            <p className="text-xs font-medium text-text-secondary">匯入模式</p>
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setMode('append')}
                className={[
                  'flex-1 rounded-md border px-3 py-2 text-sm transition-colors',
                  mode === 'append'
                    ? 'border-brand-500 bg-brand-50 text-brand-700 font-medium'
                    : 'border-border text-text-secondary hover:border-brand-300',
                ].join(' ')}
              >
                追加（跳過重複）
              </button>
              <button
                type="button"
                onClick={() => setMode('replace')}
                className={[
                  'flex-1 rounded-md border px-3 py-2 text-sm transition-colors',
                  mode === 'replace'
                    ? 'border-red-500 bg-red-50 text-red-700 font-medium'
                    : 'border-border text-text-secondary hover:border-red-300',
                ].join(' ')}
              >
                全量取代
              </button>
            </div>
          </div>

          {mode === 'replace' && (
            <Alert variant="destructive" className="py-2">
              <AlertTriangle className="h-4 w-4" />
              <AlertDescription className="text-xs">
                全量取代模式將先刪除此 Agent 下所有 FAQ，再匯入新資料，此操作不可復原。
              </AlertDescription>
            </Alert>
          )}

          <p className="text-xs text-text-muted">
            必填欄位：question、answer。category_path 為選填（用 / 分隔多層），留空則歸入「未分類」。匯入後一律為 draft 狀態。
          </p>
          {(importing || progress > 0) && <Progress value={progress} />}
          {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}
          <Button
            onClick={handleImport}
            disabled={!file || importing}
            className="w-full"
            variant={mode === 'replace' ? 'destructive' : 'default'}
          >
            {importing ? '匯入中...' : mode === 'replace' ? '清空並匯入' : '開始匯入'}
          </Button>
        </Card>

        <Card className="p-6 space-y-4">
          <h2 className="text-lg font-semibold">匯出 FAQ</h2>
          <p className="text-sm text-text-secondary">將此 Agent 下所有 FAQ（含各狀態）匯出為 xlsx。</p>
          <p className="text-xs text-text-muted">欄位：id / status / category_path / tags / question / answer / version / created_at / updated_at</p>
          <Button onClick={exportXlsx} disabled={exporting} className="w-full">
            <Download className="w-4 h-4 mr-1" strokeWidth={1.5} />
            {exporting ? '匯出中...' : '下載全量匯出（xlsx）'}
          </Button>
        </Card>
      </div>

      {result && <ImportResult result={result} />}
    </div>
  )
}
