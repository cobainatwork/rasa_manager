import { useEffect, useState, useCallback } from 'react'
import * as api from '@/api/endpoints/users'
import { extractErrorMessage } from '@/api/client'
import { toast } from 'sonner'
import type { User } from '@/api/types'

export function useUserManagement() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const reload = useCallback(() => {
    setLoading(true)
    api.listUsers()
      .then(setUsers)
      .catch((err) => toast.error(extractErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { reload() }, [reload])

  const selected = users.find((u) => u.id === selectedId) ?? null
  return { users, loading, selectedId, selected, select: setSelectedId, reload }
}
