import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, tokenStore } from '../api/client'
import type { TokenOut, UserOut } from '../api/types'
import { isLang, type Lang } from '../i18n/core'
import { useI18n } from '../i18n/context'
import { langStore } from '../i18n/storage'

interface AuthValue {
  user: UserOut | null
  ready: boolean
  signIn: (t: TokenOut) => void
  signOut: () => void
  refresh: () => Promise<void>
  /** Switch the UI language and remember it in the account (restored on sign-in elsewhere). */
  changeLanguage: (lang: Lang) => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [ready, setReady] = useState(false)
  const { lang, setLang } = useI18n()

  /** A language chosen on this device wins and is saved to the account; a device without a choice
   * adopts the account language. */
  const syncLanguage = useCallback((u: UserOut) => {
    const device = langStore.get()
    if (isLang(device)) {
      if (u.locale !== device) {
        api<UserOut>('/auth/me/locale', { method: 'PUT', body: { locale: device } }).then(setUser, () => {})
      }
    } else if (isLang(u.locale)) {
      setLang(u.locale)
    }
  }, [setLang])

  const refresh = useCallback(async () => {
    if (!tokenStore.get()) {
      setUser(null)
      setReady(true)
      return
    }
    try {
      const u = await api<UserOut>('/auth/me')
      setUser(u)
      syncLanguage(u)
    } catch {
      tokenStore.clear()
      setUser(null)
    } finally {
      setReady(true)
    }
  }, [syncLanguage])

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
      syncLanguage(t.user)
    },
    signOut: () => {
      tokenStore.clear()
      setUser(null)
    },
    changeLanguage: (l) => {
      if (l === lang) return
      setLang(l)
      if (user) api<UserOut>('/auth/me/locale', { method: 'PUT', body: { locale: l } }).then(setUser, () => {})
    },
  }), [user, ready, refresh, syncLanguage, lang, setLang])

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth outside AuthProvider')
  return ctx
}
