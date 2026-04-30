import { useState } from 'react'
import { apiClient, extractErrorMessage } from '@/api/client'

interface CreateAgentForm {
  name: string
  txt_output_path: string
  rasa_rest_url: string
  ingest_script_path: string
}

const DEFAULT_FORM: CreateAgentForm = {
  name: '',
  txt_output_path: '',
  rasa_rest_url: '',
  ingest_script_path: '',
}

function validateForm(form: CreateAgentForm): string | null {
  if (!form.name.trim()) return 'Agent 名稱為必填欄位。'
  if (!form.txt_output_path.trim()) return 'TXT 輸出路徑為必填欄位。'
  return null
}

function toPayload(form: CreateAgentForm) {
  return {
    name: form.name.trim(),
    txt_output_path: form.txt_output_path.trim(),
    rasa_rest_url: form.rasa_rest_url.trim() || null,
    ingest_script_path: form.ingest_script_path.trim() || null,
  }
}

interface Props {
  onClose: () => void
  onCreated: () => void
}

export function CreateAgentModal({ onClose, onCreated }: Props) {
  const [form, setForm] = useState<CreateAgentForm>(DEFAULT_FORM)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const update = (field: keyof CreateAgentForm) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setForm((prev) => ({ ...prev, [field]: e.target.value }))

  const handleSubmit = async () => {
    const validationError = validateForm(form)
    if (validationError) { setError(validationError); return }

    setSubmitting(true)
    setError(null)
    try {
      await apiClient.post('/api/v1/agents', toPayload(form))
      onCreated()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        <div className="p-6 border-b">
          <h2 className="text-xl font-bold">建立新 Agent</h2>
        </div>

        <div className="p-6 space-y-4">
          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded p-3">
              {error}
            </div>
          )}

          <FormField label="Agent 名稱" required>
            <input
              type="text"
              className="input w-full"
              placeholder="例如：客服機器人"
              value={form.name}
              onChange={update('name')}
            />
          </FormField>

          <FormField label="TXT 輸出路徑" required hint="容器內部路徑，同步時 .txt 檔案寫入此目錄。">
            <input
              type="text"
              className="input w-full"
              placeholder="例如：/opt/rasa_docs/agent-001"
              value={form.txt_output_path}
              onChange={update('txt_output_path')}
            />
          </FormField>

          <FormField label="Rasa Webhook URL">
            <input
              type="text"
              className="input w-full"
              placeholder="例如：http://10.2.66.88:5555/webhooks/myio/webhook"
              value={form.rasa_rest_url}
              onChange={update('rasa_rest_url')}
            />
          </FormField>

          <FormField label="Ingestion Script 路徑" hint="容器內部路徑，需已透過 volume 掛載。">
            <input
              type="text"
              className="input w-full"
              placeholder="例如：/opt/rasa_integration/ingest_kb.py"
              value={form.ingest_script_path}
              onChange={update('ingest_script_path')}
            />
          </FormField>
        </div>

        <div className="p-6 border-t flex justify-end gap-3">
          <button onClick={onClose} disabled={submitting} className="btn-ghost">
            取消
          </button>
          <button onClick={handleSubmit} disabled={submitting} className="btn-primary disabled:opacity-50">
            {submitting ? '建立中...' : '建立 Agent'}
          </button>
        </div>
      </div>
    </div>
  )
}

interface FormFieldProps {
  label: string
  required?: boolean
  hint?: string
  children: React.ReactNode
}

function FormField({ label, required, hint, children }: FormFieldProps) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {label}
        {required
          ? <span className="text-red-500 ml-0.5">*</span>
          : <span className="text-slate-400 font-normal ml-1">（選填）</span>
        }
      </label>
      {children}
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}
