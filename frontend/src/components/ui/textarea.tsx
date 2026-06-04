import * as React from "react"

import { cn } from "@/lib/utils"
import { FORM_FIELD_BASE } from "./form-field-base"

const Textarea = React.forwardRef<
  HTMLTextAreaElement,
  React.ComponentProps<"textarea">
>(({ className, ...props }, ref) => {
  return (
    <textarea
      className={cn(
        FORM_FIELD_BASE,
        // Textarea 尺寸：min-h-[60px]、py-2
        "min-h-[60px] py-2",
        className
      )}
      ref={ref}
      {...props}
    />
  )
})
Textarea.displayName = "Textarea"

export { Textarea }
