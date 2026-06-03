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
      {/* relative + 模糊光暈讓圖示有「漂浮」質感而非貼平 */}
      {Icon && (
        <div className="relative mb-6">
          <div className="absolute inset-0 bg-brand-500/10 rounded-full blur-2xl" aria-hidden />
          <Icon
            className="relative w-20 h-20 text-text-muted/40"
            strokeWidth={1}
          />
        </div>
      )}
      <h3 className="text-base font-semibold text-text-primary mb-1.5">{title}</h3>
      {description && (
        <p className="text-sm text-text-secondary mb-5 max-w-md leading-relaxed">{description}</p>
      )}
      {action}
    </div>
  )
}
