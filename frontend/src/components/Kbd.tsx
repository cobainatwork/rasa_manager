import { cn } from '@/lib/utils'

export function Kbd({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <kbd className={cn(
      'inline-flex items-center justify-center min-w-[1.5rem] h-6 px-1.5',
      'rounded border border-border-strong bg-subtle',
      'font-mono text-xs text-text-secondary',
      className
    )}>
      {children}
    </kbd>
  )
}
