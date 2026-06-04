import { forwardRef, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

interface PasswordInputProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
  className?: string
}

export const PasswordInput = forwardRef<HTMLInputElement, PasswordInputProps>(
  function PasswordInput({ className, ...props }, ref) {
    const [show, setShow] = useState(false)
    return (
      <div className="relative">
        <Input ref={ref} type={show ? 'text' : 'password'} className={cn('pr-10', className)} {...props} />
        <button
          type="button"
          onClick={() => setShow((v) => !v)}
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-text-muted hover:text-text-primary cursor-pointer"
          aria-label={show ? '隱藏密碼' : '顯示密碼'}
        >
          {show ? <EyeOff className="w-4 h-4" strokeWidth={1.5} /> : <Eye className="w-4 h-4" strokeWidth={1.5} />}
        </button>
      </div>
    )
  }
)
