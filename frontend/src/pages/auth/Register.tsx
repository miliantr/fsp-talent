import { Building2, UserRound } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import type { RegisterOut } from '../../api/types'
import { AuthShell } from './AuthShell'

export default function Register() {
  const [params] = useSearchParams()
  const nav = useNavigate()
  const [role, setRole] = useState<'candidate' | 'employer'>(params.get('role') === 'employer' ? 'employer' : 'candidate')
  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '', company_name: '' })
  const [consent, setConsent] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    if (!consent) {
      setError('Нужно согласие на обработку персональных данных')
      return
    }
    setBusy(true)
    setError(null)
    try {
      const r = await api<RegisterOut>('/auth/register', { method: 'POST', body: { ...form, role, consent_processing: consent } })
      nav('/verify', { state: { email: r.email, devCode: r.dev_code } })
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <AuthShell>
      <h1>Регистрация</h1>
      <p className="muted" style={{ marginTop: 6 }}>Уже есть аккаунт? <Link to="/login">Войдите</Link></p>
      <form className="stack-lg" style={{ marginTop: 24 }} onSubmit={submit}>
        <div className="role-pick">
          <button type="button" className={role === 'candidate' ? 'on' : ''} onClick={() => setRole('candidate')}>
            <UserRound size={20} color="var(--primary)" /><div className="bold" style={{ marginTop: 6 }}>Я кандидат</div>
            <div className="tiny muted">Пройду тест и получу приглашения</div></button>
          <button type="button" className={role === 'employer' ? 'on' : ''} onClick={() => setRole('employer')}>
            <Building2 size={20} color="var(--primary)" /><div className="bold" style={{ marginTop: 6 }}>Я работодатель</div>
            <div className="tiny muted">Найду и приглашу специалистов</div></button>
        </div>
        {role === 'candidate' ? (
          <div className="grid grid-2">
            <div className="field"><label htmlFor="fn">Имя</label><input id="fn" className="input" required value={form.first_name} onChange={set('first_name')} /></div>
            <div className="field"><label htmlFor="ln">Фамилия</label><input id="ln" className="input" required value={form.last_name} onChange={set('last_name')} /></div>
          </div>
        ) : (
          <div className="field"><label htmlFor="co">Название компании</label><input id="co" className="input" required value={form.company_name} onChange={set('company_name')} /></div>
        )}
        <div className="field"><label htmlFor="em">E-mail</label><input id="em" className="input" type="email" required value={form.email} onChange={set('email')} autoComplete="email" /></div>
        <div className="field"><label htmlFor="pw">Пароль</label><input id="pw" className="input" type="password" minLength={8} required value={form.password} onChange={set('password')} autoComplete="new-password" />
          <span className="hint">Не менее 8 символов</span></div>
        <label className="check"><input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
          <span className="small">Я даю согласие на обработку персональных данных в соответствии с 152-ФЗ. Публикацию профиля для работодателей можно включить отдельно в настройках.</span></label>
        {error && <div className="alert error">{error}</div>}
        <button className="btn lg block" disabled={busy}>{busy ? 'Создаём аккаунт…' : 'Зарегистрироваться'}</button>
      </form>
    </AuthShell>
  )
}
