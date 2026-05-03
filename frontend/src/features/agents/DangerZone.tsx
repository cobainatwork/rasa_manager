import { AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'

interface Props {
  agentName: string
  onDelete: () => void
}

export function DangerZone({ agentName, onDelete }: Props) {
  return (
    <Card className="p-6 border-red-200 border-2">
      <h2 className="font-semibold mb-2 text-red-700 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" strokeWidth={1.5} /> 危險區
      </h2>
      <p className="text-sm text-text-secondary mb-4">
        刪除後將同時清除所有 FAQ、分類、稽核日誌，且無法復原。
      </p>
      <AlertDialog>
        <AlertDialogTrigger asChild>
          <Button type="button" variant="destructive">刪除此 Agent</Button>
        </AlertDialogTrigger>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>確認刪除「{agentName}」？</AlertDialogTitle>
            <AlertDialogDescription>
              將刪除此 Agent 及其下所有 FAQ、分類、稽核日誌。此操作無法復原。
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              onClick={onDelete}
              className="bg-red-600 hover:bg-red-700"
            >
              永久刪除
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}
