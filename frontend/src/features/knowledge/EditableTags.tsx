import { useState, type KeyboardEvent } from 'react'
import { X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface Props {
  tags: string[]
  onSave: (next: string[]) => Promise<void>
}

export function EditableTags({ tags, onSave }: Props) {
  const [draft, setDraft] = useState('')

  async function add() {
    const t = draft.trim()
    if (!t || tags.includes(t)) { setDraft(''); return }
    await onSave([...tags, t])
    setDraft('')
  }

  async function remove(t: string) {
    await onSave(tags.filter((x) => x !== t))
  }

  function onKey(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      add()
    }
  }

  return (
    <div className="space-y-1.5">
      <Label>標籤</Label>
      <div className="flex flex-wrap items-center gap-2 p-2 border border-border-default rounded-md min-h-[2.5rem]">
        {tags.map((t) => (
          <Badge key={t} variant="secondary" className="gap-1">
            {t}
            <button type="button" onClick={() => remove(t)} className="hover:text-red-600" aria-label={`移除 ${t}`}>
              <X className="w-3 h-3" strokeWidth={1.5} />
            </button>
          </Badge>
        ))}
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={onKey}
          onBlur={add}
          placeholder="+ 標籤"
          className="flex-1 min-w-[100px] border-none shadow-none focus-visible:ring-0 h-7 p-0"
        />
      </div>
    </div>
  )
}
