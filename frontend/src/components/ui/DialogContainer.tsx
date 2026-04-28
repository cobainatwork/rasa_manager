import { useState } from 'react'
import { useDialogStore, type DialogEntry } from '@/store/useDialogStore'

function DialogModal({ entry }: { entry: DialogEntry }) {
  const { _resolve } = useDialogStore()
  const [inputValue, setInputValue] = useState(entry.defaultValue ?? '')

  const handleConfirm = () => {
    if (entry.type === 'prompt') {
      _resolve(entry.id, inputValue || null)
    } else {
      _resolve(entry.id, true)
    }
  }

  const handleCancel = () => {
    _resolve(entry.id, entry.type === 'prompt' ? null : false)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-sm mx-4">
        <p className="text-slate-800 mb-4 whitespace-pre-wrap text-sm leading-relaxed">
          {entry.message}
        </p>

        {entry.type === 'prompt' && (
          <input
            autoFocus
            className="input mb-4"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleConfirm()
              if (e.key === 'Escape') handleCancel()
            }}
          />
        )}

        <div className="flex justify-end gap-2">
          <button onClick={handleCancel} className="btn-secondary">
            取消
          </button>
          <button onClick={handleConfirm} className="btn-primary">
            確定
          </button>
        </div>
      </div>
    </div>
  )
}

export function DialogContainer() {
  const { dialogs } = useDialogStore()

  if (dialogs.length === 0) return null

  return <DialogModal entry={dialogs[0]} />
}
