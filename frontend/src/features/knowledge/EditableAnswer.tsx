import { useState, useEffect } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

interface Props {
  value: string
  onSave: (next: string) => Promise<void>
}

export function EditableAnswer({ value, onSave }: Props) {
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
        答案 {saving && <span className="text-xs text-text-muted">儲存中...</span>}
      </Label>
      <Textarea
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') commit()
        }}
        rows={10}
        placeholder="輸入答案內容..."
        className="resize-y min-h-[200px] font-mono text-sm"
      />
      <p className="text-xs text-text-muted">支援多行純文字。Cmd/Ctrl + Enter 立即儲存，或失焦自動儲存。</p>
    </div>
  )
}
