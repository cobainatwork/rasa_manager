import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { FORM_FIELD_BASE } from '@/components/ui/form-field-base'
import { cn } from '@/lib/utils'
import { listAgents, updateAgent, deleteAgent, testConnection, validateScript } from '@/api/endpoints/agents'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import { DangerZone } from './DangerZone'
import { AgentIntegrationFields } from './AgentIntegrationFields'
import { agentEditSchema, type AgentEditFormData as FormData } from './agentFormSchema'
import type { Agent } from '@/api/types'

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
    formState: { isDirty, isSubmitting, errors },
  } = useForm<FormData>({ resolver: zodResolver(agentEditSchema) })

  useEffect(() => {
    if (!id) return
    listAgents()
      .then((list) => {
        const found = list.find((a) => a.id === id) ?? null
        setAgent(found)
        if (found) {
          reset({
            name: found.name,
            qdrant_collection: found.qdrant_collection,
            txt_output_path: found.txt_output_path,
            rasa_rest_url: found.rasa_rest_url ?? '',
            ingest_script_path: found.ingest_script_path ?? '',
            embedding_provider: found.embedding_provider,
            embedding_model: found.embedding_model,
          })
        }
      })
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [id, reset])

  async function onSubmit(data: FormData) {
    if (!id) return
    try {
      // schema 已 transform 空字串為 null（rasa_rest_url / ingest_script_path）
      await updateAgent(id, data)
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
        <div className="sticky top-0 z-sticky bg-amber-500/[0.10] border border-amber-500/[0.25] rounded-lg p-3 mb-4 flex justify-between items-center">
          <span className="text-sm text-amber-800 font-medium">有未儲存變更</span>
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
        errors={errors}
        test={{ run: handleTestConnection, busy: testingConn }}
        validate={{ run: handleValidateScript, busy: validatingScript }}
      />

      <Card className="p-6 mb-6">
        <h2 className="font-semibold mb-1">Embedding 設定</h2>
        <p className="text-xs text-text-muted mb-4">
          切換 provider 或 model 後，下次同步請先用「清空重建」（避免 dim mismatch）。
        </p>
        <div className="grid grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label>Provider</Label>
            <select
              {...register('embedding_provider')}
              className={cn(FORM_FIELD_BASE, 'h-9 py-1')}
            >
              <option value="openai">OpenAI（雲端）</option>
              <option value="local">Local（地端 OpenAI-compatible）</option>
            </select>
            {errors.embedding_provider && (
              <p className="text-xs text-destructive">{errors.embedding_provider.message}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Model 名稱</Label>
            <Input
              {...register('embedding_model')}
              placeholder="text-embedding-3-small / bge-m3-q8_0"
            />
            {errors.embedding_model && (
              <p className="text-xs text-destructive">{errors.embedding_model.message}</p>
            )}
          </div>
        </div>
      </Card>

      <DangerZone agentName={agent.name} onDelete={handleDelete} />
    </form>
  )
}
