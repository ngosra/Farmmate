import { useEffect, useMemo, useState, type ReactNode } from 'react'
import { loginRequest, logoutRequest, refreshSession, type Me } from './api'
import { AuthContext, type AuthState, type AuthStatus } from './auth-context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [me, setMe] = useState<Me | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    refreshSession()
      .then((next) => {
        if (cancelled) return
        setMe(next)
        setStatus(next ? 'authenticated' : 'anonymous')
      })
      .catch(() => {
        if (!cancelled) setStatus('anonymous')
      })
    return () => {
      cancelled = true
    }
  }, [])

  const value = useMemo<AuthState>(
    () => ({
      status,
      me,
      error,
      async signIn(identifier, password) {
        setError(null)
        try {
          const next = await loginRequest(identifier, password)
          setMe(next)
          setStatus('authenticated')
        } catch (err) {
          const message = err instanceof Error ? err.message : 'Could not sign in.'
          setError(message)
          throw err
        }
      },
      async signOut() {
        await logoutRequest()
        setMe(null)
        setStatus('anonymous')
      },
    }),
    [status, me, error],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
