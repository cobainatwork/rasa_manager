import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { UseFormRegister } from 'react-hook-form'

interface FormData {
  name: string
  txt_output_path: string
  rasa_rest_url: string | null
  ingest_script_path: string | null
}

interface ActionState {
  run: () => Promise<void>
  busy: boolean
}

interface Props {
  register: UseFormRegister<FormData>
  test: ActionState
  validate: ActionState
}

export function AgentIntegrationFields({ register, test, validate }: Props) {
  return (
    <>
      <Card className="p-6 mb-6">
        <h2 className="font-semibold mb-4">Rasa 整合</h2>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Webhook URL</Label>
            <Input {...register('rasa_rest_url')} placeholder="http://host:port/webhooks/.../webhook" />
            <p className="text-xs text-text-muted">完整 Rasa REST webhook URL</p>
          </div>
          <Button type="button" variant="outline" onClick={test.run} disabled={test.busy}>
            {test.busy ? '測試中...' : '測試連線'}
          </Button>
        </div>
      </Card>

      <Card className="p-6 mb-6">
        <h2 className="font-semibold mb-4">Ingestion 腳本</h2>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>腳本路徑（容器內絕對路徑）</Label>
            <Input {...register('ingest_script_path')} placeholder="/opt/project/ingest_kb.py" />
          </div>
          <div className="space-y-1.5">
            <Label>TXT 輸出路徑</Label>
            <Input {...register('txt_output_path')} />
            <p className="text-xs text-text-muted">faq_export.txt 寫入此目錄</p>
          </div>
          <Button type="button" variant="outline" onClick={validate.run} disabled={validate.busy}>
            {validate.busy ? '驗證中...' : '驗證腳本存在性'}
          </Button>
        </div>
      </Card>
    </>
  )
}
