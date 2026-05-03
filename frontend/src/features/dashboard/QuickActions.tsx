import { useNavigate, useParams } from 'react-router-dom'
import { Plus, RefreshCw, MessageSquare } from 'lucide-react'
import { Card } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function QuickActions() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()

  return (
    <Card className="p-5">
      <h3 className="font-semibold mb-3">快速操作</h3>
      <div className="flex flex-wrap gap-2">
        <Button variant="outline" onClick={() => navigate(`/agents/${id}/knowledge`)}>
          <Plus className="w-4 h-4 mr-1" strokeWidth={1.5} /> 新增 FAQ
        </Button>
        <Button variant="outline" onClick={() => navigate(`/agents/${id}/sync`)}>
          <RefreshCw className="w-4 h-4 mr-1" strokeWidth={1.5} /> 觸發同步
        </Button>
        <Button variant="outline" onClick={() => navigate(`/agents/${id}/test-chat`)}>
          <MessageSquare className="w-4 h-4 mr-1" strokeWidth={1.5} /> 對話測試
        </Button>
      </div>
    </Card>
  )
}
