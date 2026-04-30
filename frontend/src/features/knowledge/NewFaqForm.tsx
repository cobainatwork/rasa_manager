import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { EditableCategory } from './EditableCategory'
import * as api from '@/api/endpoints/faqs'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { CategoryNode } from '@/api/types'

interface Props {
  agentId: string
  categoryTree: CategoryNode[]
  defaultCategoryId: string | null
  onCreated: (newFaqId: string) => void
  onCancel: () => void
}

export function NewFaqForm({ agentId, categoryTree, defaultCategoryId, onCreated, onCancel }: Props) {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [categoryId, setCategoryId] = useState(defaultCategoryId ?? '')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit() {
    if (!question.trim() || !answer.trim() || !categoryId) {
      setError('問題、答案、分類皆為必填')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const faq = await api.createFaq(agentId, {
        category_id: categoryId, question: question.trim(), answer: answer.trim(), tags: [],
      })
      toast.success('FAQ 建立成功')
      onCreated(faq.id)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-lg font-semibold">新增 FAQ</h2>

      <div className="space-y-1.5">
        <Label>問題 <span className="text-red-600">*</span></Label>
        <Textarea value={question} onChange={(e) => setQuestion(e.target.value)} rows={2} />
      </div>

      <div className="space-y-1.5">
        <Label>答案（Markdown） <span className="text-red-600">*</span></Label>
        <Textarea value={answer} onChange={(e) => setAnswer(e.target.value)} rows={6} />
      </div>

      <EditableCategory
        categoryId={categoryId}
        tree={categoryTree}
        onSave={async (id) => setCategoryId(id)}
      />

      {error && <Alert variant="destructive"><AlertDescription>{error}</AlertDescription></Alert>}

      <div className="flex justify-end gap-2 pt-2 border-t border-border-default">
        <Button variant="outline" onClick={onCancel}>取消</Button>
        <Button onClick={submit} disabled={submitting}>{submitting ? '建立中...' : '建立 FAQ'}</Button>
      </div>
    </div>
  )
}
