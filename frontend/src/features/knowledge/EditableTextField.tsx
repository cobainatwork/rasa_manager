import { useState, useEffect } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'

interface Props {
  label: string
  value: string
  onSave: (next: string) => Promise<void>
  rows?: number
  /** 是否使用等寬字型 + 可垂直拉伸的多行樣式（適合 Answer 區） */
  monoFont?: boolean
  /** 提示文字（顯示於 Textarea 下方） */
  helpText?: string
  placeholder?: string
}

/**
 * 共用「失焦自動儲存 / Cmd+Enter 立即儲存」可編輯欄位。
 *
 * 取代 EditableQuestion / EditableAnswer：
 * - rows + label 由 caller 控制
 * - monoFont = true 時套用等寬字型 + min-h-[200px]（原 EditableAnswer 樣式）
 * - 失焦時若無變更則跳過呼叫 onSave
 */
export function EditableTextField({
  label,
  value,
  onSave,
  rows = 2,
  monoFont = false,
  helpText,
  placeholder,
}: Props) {
  const [local, setLocal] = useState(value)
  const [saving, setSaving] = useState(false)

  useEffect(() => { setLocal(value) }, [value])

  async function commit() {
    if (local === value) return
    setSaving(true)
    try { await onSave(local) } finally { setSaving(false) }
  }

  return (
    <div className="space-y-1.5">
      <Label className="flex items-center gap-2">
        {label} {saving && <span className="text-xs text-text-muted">儲存中...</span>}
      </Label>
      <Textarea
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') commit()
        }}
        rows={rows}
        placeholder={placeholder}
        className={cn(monoFont && 'resize-y min-h-[200px] font-mono text-sm')}
      />
      {helpText && <p className="text-xs text-text-muted">{helpText}</p>}
    </div>
  )
}
