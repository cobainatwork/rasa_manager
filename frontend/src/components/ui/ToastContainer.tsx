import { useToastStore } from '@/store/useToastStore'

const TYPE_STYLES = {
  success: 'bg-green-600 text-white',
  error: 'bg-red-600 text-white',
  info: 'bg-slate-700 text-white',
}

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm w-full">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`flex items-start justify-between gap-3 rounded-lg px-4 py-3 shadow-lg text-sm ${TYPE_STYLES[t.type]}`}
        >
          <span className="flex-1 break-words">{t.message}</span>
          <button
            onClick={() => removeToast(t.id)}
            className="shrink-0 opacity-70 hover:opacity-100 font-bold leading-none"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  )
}
