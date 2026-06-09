import { EditableTextField } from './EditableTextField'

interface Props {
  value: string
  onSave: (next: string) => Promise<void>
}

export function EditableAnswer({ value, onSave }: Props) {
  return (
    <EditableTextField
      label="答案"
      value={value}
      onSave={onSave}
      rows={10}
      monoFont
      placeholder="輸入答案內容..."
      helpText="支援多行純文字。Cmd/Ctrl + Enter 立即儲存，或失焦自動儲存。"
    />
  )
}
