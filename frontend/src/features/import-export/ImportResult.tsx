import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import { Card } from '@/components/ui/card'

interface ImportResultData {
  imported: number
  skipped: number
  errors: { row: number; reason: string }[]
  new_categories: string[]
}

interface StatProps {
  icon: typeof CheckCircle2
  color: string
  label: string
  value: number
}

function Stat({ icon: Icon, color, label, value }: StatProps) {
  return (
    <span className={`flex items-center gap-1 font-medium ${color}`}>
      <Icon className="w-4 h-4" strokeWidth={1.5} /> {label}：{value}
    </span>
  )
}

export function ImportResult({ result }: { result: ImportResultData }) {
  return (
    <Card className="p-4 space-y-4">
      <div className="flex flex-wrap gap-4 text-sm">
        <Stat icon={CheckCircle2} color="text-emerald-700" label="成功匯入" value={result.imported} />
        <Stat icon={AlertTriangle} color="text-amber-700" label="跳過重複" value={result.skipped} />
        <Stat icon={XCircle} color="text-red-700" label="失敗" value={result.errors.length} />
      </div>

      {result.new_categories.length > 0 && (
        <div className="text-sm">
          <p className="font-medium mb-1">自動建立分類：</p>
          <ul className="list-disc list-inside text-text-secondary">
            {result.new_categories.map((c) => <li key={c}>{c}</li>)}
          </ul>
        </div>
      )}

      {result.errors.length > 0 && (
        <div className="text-sm">
          <p className="font-medium text-red-700 mb-2">錯誤明細：</p>
          <table className="w-full text-xs">
            <thead>
              <tr>
                <th className="text-left w-16">列</th>
                <th className="text-left">原因</th>
              </tr>
            </thead>
            <tbody>
              {result.errors.map((e, i) => (
                <tr key={i} className="border-t border-border-default">
                  <td className="py-1">{e.row}</td>
                  <td className="py-1 text-red-800">{e.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}
