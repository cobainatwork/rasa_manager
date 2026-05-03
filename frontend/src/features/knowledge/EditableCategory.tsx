import { useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Command, CommandInput, CommandItem, CommandList, CommandEmpty } from '@/components/ui/command'
import { flattenCategories } from '@/lib/categories'
import { cn } from '@/lib/utils'
import type { CategoryNode } from '@/api/types'

interface Props {
  categoryId: string
  tree: CategoryNode[]
  onSave: (next: string) => Promise<void>
}

export function EditableCategory({ categoryId, tree, onSave }: Props) {
  const [open, setOpen] = useState(false)
  const flat = flattenCategories(tree)
  const current = flat.find((c) => c.id === categoryId)

  return (
    <div className="space-y-1.5">
      <Label>分類</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="outline" role="combobox" className="w-full justify-between">
            {current ? current.path : '選擇分類'}
            <ChevronDown className="w-4 h-4 ml-2 opacity-50" strokeWidth={1.5} />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="p-0" align="start">
          <Command>
            <CommandInput placeholder="搜尋分類路徑..." />
            <CommandList>
              <CommandEmpty>找不到分類</CommandEmpty>
              {flat.map((c) => (
                <CommandItem
                  key={c.id}
                  value={c.path}
                  onSelect={async () => {
                    setOpen(false)
                    if (c.id !== categoryId) await onSave(c.id)
                  }}
                >
                  <Check className={cn('w-4 h-4 mr-2', c.id === categoryId ? 'opacity-100' : 'opacity-0')} strokeWidth={1.5} />
                  {c.path}
                </CommandItem>
              ))}
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
    </div>
  )
}
