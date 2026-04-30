import { useDropzone } from 'react-dropzone'
import { Upload, File as FileIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

interface Props {
  onFileSelected: (file: File) => void
  selectedFile: File | null
}

export function ImportDropzone({ onFileSelected, selectedFile }: Props) {
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: { 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'] },
    maxSize: 10 * 1024 * 1024,
    multiple: false,
    onDrop: (files) => files[0] && onFileSelected(files[0]),
  })

  return (
    <div
      {...getRootProps()}
      className={cn(
        'border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors duration-fast',
        isDragActive ? 'border-brand-500 bg-brand-50' : 'border-border-strong hover:border-brand-500'
      )}
    >
      <input {...getInputProps()} />
      {selectedFile ? (
        <div className="flex items-center justify-center gap-2 text-sm">
          <FileIcon className="w-5 h-5 text-brand-500" strokeWidth={1.5} />
          <span className="font-medium">{selectedFile.name}</span>
          <span className="text-text-muted">({(selectedFile.size / 1024).toFixed(0)} KB)</span>
        </div>
      ) : (
        <>
          <Upload className="w-10 h-10 mx-auto mb-2 text-text-muted" strokeWidth={1.5} />
          <p className="text-sm font-medium">{isDragActive ? '放開以上傳' : '拖放 .xlsx 檔案或點此選取'}</p>
          <p className="text-xs text-text-muted mt-1">上限：10 MB / 5000 列</p>
        </>
      )}
    </div>
  )
}
