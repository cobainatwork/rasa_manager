import { useState, useEffect } from 'react'
import MDEditor from '@uiw/react-md-editor'
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
    <div className="space-y-1.5" data-color-mode="light">
      <Label className="flex items-center gap-2">
        答案（Markdown）{saving && <span className="text-xs text-text-muted">儲存中...</span>}
      </Label>
      <MDEditor
        value={local}
        onChange={(v) => setLocal(v ?? '')}
        onBlur={commit}
        preview="edit"
        height={300}
      />
    </div>
  )
}
