import { useState } from 'react'
import * as api from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { User } from '@/api/types'
import { useApiResource } from '@/hooks/useApiResource'

export function useUserManagement() {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const { data, loading, reload } = useApiResource<User[]>(
    () => api.listUsers(),
    [],
    {
      initialLoading: true,
      fallback: [],
      silentError: true,
      onError: (err) => toast.error(extractErrorMessage(err)),
    },
  )

  const users: User[] = data ?? []
  const selected = users.find((u) => u.id === selectedId) ?? null
  return { users, loading, selectedId, selected, select: setSelectedId, reload }
}
