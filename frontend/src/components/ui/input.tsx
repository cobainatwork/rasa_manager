import * as React from "react"

import { cn } from "@/lib/utils"
import { FORM_FIELD_BASE } from "./form-field-base"

const Input = React.forwardRef<HTMLInputElement, React.ComponentProps<"input">>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          FORM_FIELD_BASE,
          // Input 尺寸：h-9、py-1，並含 file input 樣式覆蓋
          "h-9 py-1 file:border-0 file:bg-transparent file:text-sm file:font-medium file:text-foreground",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }
