import { useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { useAuthStore } from '@/store/useAuthStore'
import { extractErrorMessage } from '@/api/client'

interface UseLoginResult {
  submit: (username: string, password: string) => Promise<void>
  isSubmitting: boolean
  error: string | null
  clearError: () => void
}

export function useLogin(): UseLoginResult {
  const navigate = useNavigate()
  const location = useLocation()
  const login = useAuthStore((s) => s.login)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function submit(username: string, password: string) {
    setIsSubmitting(true)
    setError(null)
    try {
      await login(username, password)
      const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname ?? '/agents'
      navigate(from, { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsSubmitting(false)
    }
  }

  return { submit, isSubmitting, error, clearError: () => setError(null) }
}
