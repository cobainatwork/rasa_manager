import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export interface EmptyStateProps {
  icon?: LucideIcon
  title: string
  description?: string
  action?: React.ReactNode
  className?: string
}

export function EmptyState({ icon: Icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={cn('flex flex-col items-center justify-center text-center py-16', className)}>
      {Icon && (
        <Icon
          className="w-20 h-20 text-text-muted/70 mb-6"
          strokeWidth={1}
        />
      )}
      <h3 className="text-base font-semibold text-text-primary mb-1.5">{title}</h3>
      {description && (
        <p className="text-sm text-text-secondary mb-5 max-w-md leading-relaxed">{description}</p>
      )}
      {action}
    </div>
  )
}
