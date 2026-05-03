import { useState, useEffect } from 'react'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'

interface Props {
  value: string
  onSave: (next: string) => Promise<void>
}

export function EditableQuestion({ value, onSave }: Props) {
  const [local, setLocal] = useState(value)
  const [saving, setSaving] = useState(false)

  useEffect(() => { setLocal(value) }, [value])

  async function handleBlur() {
    if (local === value) return
    setSaving(true)
    try { await onSave(local) } finally { setSaving(false) }
  }

  return (
    <div className="space-y-1.5">
      <Label className="flex items-center gap-2">
        問題 {saving && <span className="text-xs text-text-muted">儲存中...</span>}
      </Label>
      <Textarea
        value={local}
        onChange={(e) => setLocal(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={(e) => {
          if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') handleBlur()
        }}
        rows={2}
      />
    </div>
  )
}
