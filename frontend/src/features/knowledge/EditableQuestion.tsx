import { EditableTextField } from './EditableTextField'

interface Props {
  value: string
  onSave: (next: string) => Promise<void>
}

export function EditableQuestion({ value, onSave }: Props) {
  return <EditableTextField label="問題" value={value} onSave={onSave} rows={2} />
}
