import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { listAgents, updateAgent, deleteAgent, testConnection, validateScript } from '@/api/endpoints/agents'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { DangerZone } from './DangerZone'
import { AgentIntegrationFields } from './AgentIntegrationFields'
import type { Agent } from '@/api/types'

const schema = z.object({
  name: z.string().min(1).max(100),
  txt_output_path: z.string().min(1).max(255),
  rasa_rest_url: z
    .string()
    .nullable()
    .refine(
      (v) => !v || v.startsWith('http://') || v.startsWith('https://'),
      { message: 'Webhook URL 必須以 http:// 或 https:// 開頭' }
    ),
  ingest_script_path: z.string().nullable(),
})
type FormData = z.infer<typeof schema>

export function AgentSettingsPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [agent, setAgent] = useState<Agent | null>(null)
  const [loading, setLoading] = useState(true)
  const [testingConn, setTestingConn] = useState(false)
  const [validatingScript, setValidatingScript] = useState(false)

  const {
    register,
    handleSubmit,
    reset,
    formState: { isDirty, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  useEffect(() => {
    if (!id) return
    listAgents()
      .then((list) => {
        const found = list.find((a) => a.id === id) ?? null
        setAgent(found)
        if (found) {
          reset({
            name: found.name,
            txt_output_path: found.txt_output_path,
            rasa_rest_url: found.rasa_rest_url ?? '',
            ingest_script_path: found.ingest_script_path ?? '',
          })
        }
      })
      .finally(() => setLoading(false))
  }, [id, reset])

  async function onSubmit(data: FormData) {
    if (!id) return
    try {
      await updateAgent(id, {
        ...data,
        rasa_rest_url: data.rasa_rest_url || null,
        ingest_script_path: data.ingest_script_path || null,
      })
      toast.success('已儲存')
      reset(data)
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  async function handleTestConnection() {
    if (!id) return
    setTestingConn(true)
    try {
      const result = await testConnection(id)
      if (result.ok) toast.success(`連線成功（${result.latency_ms}ms）`)
      else toast.error(`連線失敗：${result.error ?? `HTTP ${result.status_code}`}`)
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setTestingConn(false)
    }
  }

  async function handleValidateScript() {
    if (!id) return
    setValidatingScript(true)
    try {
      const result = await validateScript(id)
      if (result.exists && result.executable) toast.success(`腳本存在（${result.size_bytes} bytes）`)
      else toast.error(result.error ?? `腳本問題：exists=${result.exists}, executable=${result.executable}`)
    } catch (err) {
      toast.error(extractErrorMessage(err))
    } finally {
      setValidatingScript(false)
    }
  }

  async function handleDelete() {
    if (!id) return
    try {
      await deleteAgent(id)
      toast.success('Agent 已刪除')
      navigate('/agents')
    } catch (err) {
      toast.error(extractErrorMessage(err))
    }
  }

  if (loading) return <div className="p-8"><Skeleton className="h-96" /></div>
  if (!agent) return <div className="p-8">Agent 不存在</div>

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="p-8 max-w-3xl">
      {isDirty && (
        <div className="sticky top-0 z-50 bg-amber-50 border border-amber-200 rounded-md p-3 mb-4 flex justify-between items-center">
          <span className="text-sm text-amber-900">有未儲存變更</span>
          <Button type="submit" disabled={isSubmitting} size="sm">儲存</Button>
        </div>
      )}

      <h1 className="text-2xl font-bold mb-6">Agent 設定：{agent.name}</h1>

      <Card className="p-6 mb-6">
        <h2 className="font-semibold mb-4">基本資訊</h2>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Agent 名稱</Label>
            <Input {...register('name')} />
          </div>
          <div className="space-y-1.5">
            <Label>建立時間</Label>
            <Input value={agent.created_at ?? '—'} disabled />
          </div>
        </div>
      </Card>

      <AgentIntegrationFields
        register={register}
        test={{ run: handleTestConnection, busy: testingConn }}
        validate={{ run: handleValidateScript, busy: validatingScript }}
      />

      <DangerZone agentName={agent.name} onDelete={handleDelete} />
    </form>
  )
}
