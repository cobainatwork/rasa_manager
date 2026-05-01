import { useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { useKeyboardShortcut } from '@/hooks/useKeyboardShortcut'
import { Kbd } from './Kbd'

interface Shortcut { keys: string[]; desc: string; section: string }

const SHORTCUTS: Shortcut[] = [
  { section: '全域', keys: ['/'], desc: '聚焦搜尋框' },
  { section: '全域', keys: ['n'], desc: '新增 FAQ' },
  { section: '全域', keys: ['?'], desc: '顯示此速查表' },
  { section: 'FAQ 列表', keys: ['↑', '↓'], desc: '切換選中列' },
  { section: 'FAQ 列表', keys: ['j', 'k'], desc: '同上下鍵（vim 風）' },
  { section: 'FAQ 列表', keys: ['Enter'], desc: '進入編輯' },
  { section: 'FAQ 列表', keys: ['x'], desc: '切換 checkbox' },
  { section: 'FAQ 列表', keys: ['g', 'g'], desc: '跳至首列' },
  { section: 'FAQ 列表', keys: ['G'], desc: '跳至末列' },
  { section: 'FAQ 編輯', keys: ['Esc'], desc: '取消編輯' },
  { section: 'FAQ 編輯', keys: ['⌘/Ctrl', 'S'], desc: '立即儲存' },
  { section: 'FAQ 編輯', keys: ['⌘/Ctrl', 'Enter'], desc: '儲存並下一筆' },
]

// N11：分群在模組層計算一次，避免每次 render 都 reduce
const SHORTCUTS_BY_GROUP: Record<string, Shortcut[]> = SHORTCUTS.reduce<Record<string, Shortcut[]>>(
  (acc, s) => {
    (acc[s.section] ??= []).push(s)
    return acc
  },
  {},
)

export function KeyboardShortcuts() {
  const [open, setOpen] = useState(false)
  useKeyboardShortcut('?', () => setOpen(true), { shift: true })

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="max-w-lg">
        <DialogHeader><DialogTitle>鍵盤快捷鍵</DialogTitle></DialogHeader>
        <div className="space-y-4">
          {Object.entries(SHORTCUTS_BY_GROUP).map(([section, items]) => (
            <div key={section}>
              <h4 className="text-sm font-semibold text-text-secondary mb-2">{section}</h4>
              <ul className="space-y-1.5">
                {items.map((s) => (
                  <li key={s.desc} className="flex justify-between items-center text-sm">
                    <span className="text-text-primary">{s.desc}</span>
                    <span className="flex gap-1">
                      {s.keys.map((k) => <Kbd key={k}>{k}</Kbd>)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}
