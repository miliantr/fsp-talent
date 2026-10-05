import { MailCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import type { RegisterOut, TokenOut } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { useI18n } from '../../i18n/context'
import { AuthShell } from './AuthShell'

export default function Verify() {
  const loc = useLocation() as { state?: { email?: string; devCode?: string | null } }
  const { signIn } = useAuth()
  const { t } = useI18n()
  const nav = useNavigate()
  const [email, setEmail] = useState(loc.state?.email ?? '')
  const [code, setCode] = useState('')
  const [devCode, setDevCode] = useState(loc.state?.devCode ?? null)
  const [error, setError] = useState<string | null>(null)
  const [info, setInfo] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = await api<TokenOut>('/auth/verify-email', { method: 'POST', body: { email, code } })
      signIn(res)
      nav(res.user.role === 'candidate' ? '/candidate' : '/employer/company')
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  const resend = async () => {
    try {
      const r = await api<RegisterOut>('/auth/resend-code', { method: 'POST', body: { email } })
      setDevCode(r.dev_code ?? null)
      setInfo(t('auth.verify.resent'))
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <AuthShell>
      <div className="empty" style={{ padding: '0 0 12px', textAlign: 'left' }}><div className="icon" style={{ margin: 0 }}><MailCheck size={26} /></div></div>
      <h1>{t('auth.verify.title')}</h1>
      <p className="muted" style={{ marginTop: 6 }}>{t('auth.verify.sent')} <b>{email || t('auth.verify.yourInbox')}</b>.</p>
      {devCode && (
        <div className="alert violet" style={{ marginTop: 16 }}>
          <span>{t('auth.verify.demo')} <b className="mono" style={{ fontSize: 16 }}>{devCode}</b>
            <button type="button" className="btn sm secondary" style={{ marginLeft: 10 }} onClick={() => setCode(devCode)}>{t('auth.verify.fill')}</button></span>
        </div>
      )}
      <form className="stack-lg" style={{ marginTop: 20 }} onSubmit={submit}>
        {!loc.state?.email && (
          <div className="field"><label htmlFor="em">{t('auth.email')}</label><input id="em" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        )}
        <div className="field"><label htmlFor="code">{t('auth.verify.code')}</label>
          <input id="code" className="input code-input" inputMode="numeric" maxLength={6} required value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} autoFocus /></div>
        {error && <div className="alert error">{error}</div>}
        {info && <div className="alert success">{info}</div>}
        <button className="btn lg block" disabled={busy || code.length !== 6}>{busy ? t('auth.verify.busy') : t('auth.verify.submit')}</button>
        <button type="button" className="btn ghost block" onClick={resend} disabled={!email}>{t('auth.verify.resend')}</button>
      </form>
    </AuthShell>
  )
}
