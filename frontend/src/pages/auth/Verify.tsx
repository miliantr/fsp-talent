import { MailCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import type { RegisterOut, TokenOut } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { AuthShell } from './AuthShell'

export default function Verify() {
  const loc = useLocation() as { state?: { email?: string; devCode?: string | null } }
  const { signIn } = useAuth()
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
      const t = await api<TokenOut>('/auth/verify-email', { method: 'POST', body: { email, code } })
      signIn(t)
      nav(t.user.role === 'candidate' ? '/candidate' : '/employer/company')
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
      setInfo('Новый код отправлен')
    } catch (err) {
      setError(errorMessage(err))
    }
  }

  return (
    <AuthShell>
      <div className="empty" style={{ padding: '0 0 12px', textAlign: 'left' }}><div className="icon" style={{ margin: 0 }}><MailCheck size={26} /></div></div>
      <h1>Подтвердите e-mail</h1>
      <p className="muted" style={{ marginTop: 6 }}>Мы отправили 6-значный код на <b>{email || 'вашу почту'}</b>.</p>
      {devCode && (
        <div className="alert violet" style={{ marginTop: 16 }}>
          <span>Демо-режим: письмо не отправляется наружу, код — <b className="mono" style={{ fontSize: 16 }}>{devCode}</b>
            <button type="button" className="btn sm secondary" style={{ marginLeft: 10 }} onClick={() => setCode(devCode)}>Подставить</button></span>
        </div>
      )}
      <form className="stack-lg" style={{ marginTop: 20 }} onSubmit={submit}>
        {!loc.state?.email && (
          <div className="field"><label htmlFor="em">E-mail</label><input id="em" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} /></div>
        )}
        <div className="field"><label htmlFor="code">Код подтверждения</label>
          <input id="code" className="input code-input" inputMode="numeric" maxLength={6} required value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))} autoFocus /></div>
        {error && <div className="alert error">{error}</div>}
        {info && <div className="alert success">{info}</div>}
        <button className="btn lg block" disabled={busy || code.length !== 6}>{busy ? 'Проверяем…' : 'Подтвердить'}</button>
        <button type="button" className="btn ghost block" onClick={resend} disabled={!email}>Отправить код ещё раз</button>
      </form>
    </AuthShell>
  )
}
