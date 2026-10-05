import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError, errorMessage } from '../../api/client'
import type { TokenOut } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { useI18n } from '../../i18n/context'
import { AuthShell } from './AuthShell'

export default function Login() {
  const { signIn } = useAuth()
  const { t } = useI18n()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = await api<TokenOut>('/auth/login', { method: 'POST', body: { email, password } })
      signIn(res)
      nav(res.user.role === 'candidate' ? '/candidate' : '/employer')
    } catch (err) {
      if (err instanceof ApiError && err.code === 'email_not_verified') {
        nav('/verify', { state: { email } })
        return
      }
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell>
      <h1>{t('auth.login.title')}</h1>
      <p className="muted" style={{ marginTop: 6 }}>{t('auth.login.noAccount')} <Link to="/register">{t('auth.login.toRegister')}</Link></p>
      <form className="stack-lg" style={{ marginTop: 24 }} onSubmit={submit}>
        <div className="field"><label htmlFor="email">{t('auth.email')}</label>
          <input id="email" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></div>
        <div className="field"><label htmlFor="pwd">{t('auth.password')}</label>
          <input id="pwd" className="input" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></div>
        {error && <div className="alert error">{error}</div>}
        <button className="btn lg block" disabled={busy}>{busy ? t('auth.login.busy') : t('auth.login.submit')}</button>
        <p className="small muted center">{t('auth.login.demoHint')} <Link to="/">{t('auth.login.demoLink')}</Link></p>
      </form>
    </AuthShell>
  )
}
