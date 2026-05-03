interface DotProps {
  delay: number
}

function Dot({ delay }: DotProps) {
  return (
    <span
      className="w-1.5 h-1.5 rounded-full bg-text-muted animate-bounce"
      style={{ animationDelay: `${delay}s` }}
    />
  )
}

export function TypingIndicator() {
  return (
    <div className="flex justify-end">
      <div className="bg-subtle rounded-2xl px-4 py-3 flex items-center gap-1">
        <Dot delay={0} /><Dot delay={0.15} /><Dot delay={0.3} />
      </div>
    </div>
  )
}
