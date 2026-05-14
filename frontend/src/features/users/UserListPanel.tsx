import { useState } from 'react'
import { Plus, Search, ShieldCheck, User as UserIcon } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ScrollArea } from '@/components/ui/scroll-area'
import { cn } from '@/lib/utils'
import { AddUserInlineForm } from './AddUserInlineForm'
import type { User } from '@/api/types'

interface Props {
  users: User[]
  loading: boolean
  selectedId: string | null
  onSelect: (id: string) => void
  onUserCreated: () => void
}

export function UserListPanel({ users, loading, selectedId, onSelect, onUserCreated }: Props) {
  const [showAdd, setShowAdd] = useState(false)
  const [search, setSearch] = useState('')

  const filtered = users.filter((u) => u.username.toLowerCase().includes(search.toLowerCase()))

  return (
    <aside className="w-80 border-r border-border-default bg-surface flex flex-col">
      <div className="p-3 space-y-2 border-b border-border-default">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-semibold">使用者列表</h2>
          {!showAdd && (
            <Button size="sm" onClick={() => setShowAdd(true)}>
              <Plus className="w-3.5 h-3.5 mr-1" strokeWidth={1.5} /> 新增
            </Button>
          )}
        </div>
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-text-muted" strokeWidth={1.5} />
          <Input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="搜尋帳號..." className="pl-7 h-8 text-sm" />
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-3">
          {showAdd && (
            <AddUserInlineForm
              onCreated={() => { setShowAdd(false); onUserCreated() }}
              onCancel={() => setShowAdd(false)}
            />
          )}

          {loading && (
            <div className="space-y-2">{[1, 2, 3].map((i) => <Skeleton key={i} className="h-10" />)}</div>
          )}

          {!loading && filtered.length === 0 && (
            <p className="text-xs text-text-muted text-center py-4">無使用者</p>
          )}

          {!loading && filtered.map((user) => (
            <button
              key={user.id}
              type="button"
              onClick={() => onSelect(user.id)}
              className={cn(
                'w-full flex items-center gap-2 p-2 rounded text-sm cursor-pointer text-left transition-colors',
                selectedId === user.id
                  ? 'bg-brand-500/[0.10] shadow-[inset_3px_0_0_#007AFF] text-brand-700'
                  : 'hover:bg-black/[0.04]'
              )}
            >
              {user.is_superadmin
                ? <ShieldCheck className="w-4 h-4 text-purple-600" strokeWidth={1.5} />
                : <UserIcon className="w-4 h-4 text-text-muted" strokeWidth={1.5} />}
              <span className="flex-1 truncate">{user.username}</span>
              {!user.is_active && <span className="text-xs text-red-600">停用</span>}
            </button>
          ))}
        </div>
      </ScrollArea>
    </aside>
  )
}
