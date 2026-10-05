import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, tokenStore } from '../api/client'
import type { TokenOut, UserOut } from '../api/types'

interface AuthValue {
  user: UserOut | null
  ready: boolean
  signIn: (t: TokenOut) => void
  signOut: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [ready, setReady] = useState(false)

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setUser(null)
      setReady(true)
      return
    }
    try {
      setUser(await api<UserOut>('/auth/me'))
    } catch {
      tokenStore.clear()
      setUser(null)
    } finally {
      setReady(true)
    }
  }, [])

  useEffect(() => {
    void refresh()
    const onExpired = () => setUser(null)
    window.addEventListener('auth:expired', onExpired)
    return () => window.removeEventListener('auth:expired', onExpired)
  }, [refresh])

  const value = useMemo<AuthValue>(() => ({
    user,
    ready,
    refresh,
    signIn: (t) => {
      tokenStore.set(t.access_token)
      setUser(t.user)
    },
    signOut: () => {
      tokenStore.clear()
      setUser(null)
    },
  }), [user, ready, refresh])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
