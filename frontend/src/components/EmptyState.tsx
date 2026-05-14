import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  icon: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-12', className)}>
      <div className="w-14 h-14 rounded-2xl bg-black/[0.04] flex items-center justify-center mb-4">
        <Icon className="w-7 h-7 text-text-muted" strokeWidth={1.5} />
      </div>
      <h3 className="text-base font-semibold text-text-primary mb-1">{title}</h3>
      {description && <p className="text-sm text-text-secondary mb-4 max-w-md">{description}</p>}
      {action}
    </div>
  )
}
