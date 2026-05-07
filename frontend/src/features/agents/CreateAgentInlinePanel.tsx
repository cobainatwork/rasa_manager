import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { X } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { createAgent } from '@/api/endpoints/agents'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'

const schema = z.object({
  name: z.string().min(1, '必填').max(100, '最多 100 字'),
  txt_output_path: z.string().min(1, '必填').max(255, '最多 255 字'),
  rasa_rest_url: z
    .string()
    .optional()
    .refine(
      (v) => !v || v.startsWith('http://') || v.startsWith('https://'),
      { message: 'Webhook URL 必須以 http:// 或 https:// 開頭' }
    ),
  ingest_script_path: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface Props {
  onCreated: () => void
  onCancel: () => void
}

export function CreateAgentInlinePanel({ onCreated, onCancel }: Props) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  async function onSubmit(data: FormData) {
    setSubmitting(true)
    setError(null)
    try {
      await createAgent({
        name: data.name,
        txt_output_path: data.txt_output_path,
        rasa_rest_url: data.rasa_rest_url || null,
        ingest_script_path: data.ingest_script_path || null,
      })
      toast.success('Agent 建立成功')
      onCreated()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Card className="p-6 mb-6 border-brand-500 border-2">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-semibold">建立新 Agent</h2>
        <Button variant="ghost" size="icon" onClick={onCancel} aria-label="取消">
          <X className="w-4 h-4" strokeWidth={1.5} />
        </Button>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="grid grid-cols-2 gap-4">
        <Field label="Agent 名稱" required error={errors.name?.message}>
          <Input {...register('name')} placeholder="例如：客服機器人" />
        </Field>
        <Field label="TXT 輸出路徑" required error={errors.txt_output_path?.message}>
          <Input {...register('txt_output_path')} placeholder="/opt/sap" />
        </Field>
        <Field label="Rasa Webhook URL" error={errors.rasa_rest_url?.message}>
          <Input {...register('rasa_rest_url')} placeholder="http://10.2.66.88:5555/webhooks/myio/webhook" />
        </Field>
        <Field label="Ingestion 腳本路徑" error={errors.ingest_script_path?.message}>
          <Input {...register('ingest_script_path')} placeholder="/opt/project/ingest_kb.py" />
        </Field>

        {error && (
          <div className="col-span-2">
            <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>
          </div>
        )}

        <div className="col-span-2 flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onCancel}>取消</Button>
          <Button type="submit" disabled={submitting}>{submitting ? '建立中...' : '建立 Agent'}</Button>
        </div>
      </form>
    </Card>
  )
}

function Field({ label, required, error, children }: {
  label: string
  required?: boolean
  error?: string
  children: React.ReactNode
}) {
  return (
    <div className="space-y-1.5">
      <Label>{label}{required && <span className="text-red-600 ml-1">*</span>}</Label>
      {children}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}
