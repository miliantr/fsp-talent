import { ArrowRight, BadgeCheck, Building2, ClipboardCheck, Handshake, ShieldCheck, Sparkles, Trophy, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { TokenOut } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { Logo } from '../components/AppLayout'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import type { MessageKey } from '../i18n/core'
import { useI18n } from '../i18n/context'

const DEMO = [
  { email: 'candidate@demo.ru', role: 'candidate', key: 'candidate' },
  { email: 'fresh@demo.ru', role: 'candidate', key: 'fresh' },
  { email: 'hr@demo.ru', role: 'employer', key: 'employer' },
] as const

const FLOW = [
  { icon: <UserRound size={20} />, key: 'survey' },
  { icon: <ClipboardCheck size={20} />, key: 'test' },
  { icon: <BadgeCheck size={20} />, key: 'category' },
  { icon: <Sparkles size={20} />, key: 'shortlist' },
  { icon: <Handshake size={20} />, key: 'invitation' },
] as const

export default function Landing() {
  const { user, signIn } = useAuth()
  const { t } = useI18n()
  const nav = useNavigate()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const demoLogin = async (email: string) => {
    setBusy(email)
    setError(null)
    try {
      const res = await api<TokenOut>('/auth/login', { method: 'POST', body: { email, password: 'demo12345' } })
      signIn(res)
      nav(res.user.role === 'candidate' ? '/candidate' : '/employer')
    } catch (e) {
      setError(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div>
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-nav">
            <Link to="/" className="brand"><span className="brand-mark"><Logo /></span>
              <span><div className="brand-name">FSP Talent</div><div className="brand-sub">{t('landing.brandSub')}</div></span></Link>
            <div className="row">
              <LanguageSwitcher tone="light" />
              {user ? (
                <Link className="btn white" to={user.role === 'candidate' ? '/candidate' : '/employer'}>{t('landing.myCabinet')} <ArrowRight size={16} /></Link>
              ) : (
                <><Link className="btn light" to="/login">{t('landing.signIn')}</Link><Link className="btn white" to="/register">{t('landing.register')}</Link></>
              )}
            </div>
          </div>
          <div className="pill" style={{ marginTop: 48 }}><ShieldCheck size={15} />{t('landing.pill')}</div>
          <h1>{t('landing.title')}</h1>
          <p className="lead">{t('landing.lead')}</p>
          <div className="row wrap" style={{ marginTop: 30, gap: 12 }}>
            <Link className="btn white lg" to="/register?role=candidate"><UserRound size={18} />{t('landing.ctaCandidate')}</Link>
            <Link className="btn light lg" to="/register?role=employer"><Building2 size={18} />{t('landing.ctaEmployer')}</Link>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <h2>{t('landing.howTitle')}</h2>
        <p className="muted" style={{ marginTop: 6 }}>{t('landing.howSub')}</p>
        <div className="flow" style={{ marginTop: 22 }}>
          {FLOW.map((f, i) => (
            <div key={f.key} className="card">
              <div className="row between"><span className="step-num">{i + 1}</span><span style={{ color: 'var(--primary)' }}>{f.icon}</span></div>
              <h3 style={{ marginTop: 14 }}>{t(`landing.flow.${f.key}.title` as MessageKey)}</h3>
              <p className="small muted" style={{ marginTop: 4 }}>{t(`landing.flow.${f.key}.text` as MessageKey)}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-3" style={{ marginTop: 36 }}>
          <div className="card"><h3 className="row"><ClipboardCheck size={18} color="var(--primary)" />{t('landing.feature.test.title')}</h3>
            <p className="small muted" style={{ marginTop: 8 }}>{t('landing.feature.test.text')}</p></div>
          <div className="card"><h3 className="row"><Sparkles size={18} color="var(--primary)" />{t('landing.feature.matching.title')}</h3>
            <p className="small muted" style={{ marginTop: 8 }}>{t('landing.feature.matching.text')}</p></div>
          <div className="card"><h3 className="row"><Trophy size={18} color="var(--accent)" />{t('landing.feature.fsp.title')}</h3>
            <p className="small muted" style={{ marginTop: 8 }}>{t('landing.feature.fsp.text')}</p></div>
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
        <div className="card" style={{ padding: 26 }}>
          <div className="row between wrap">
            <div><h2>{t('landing.demo.title')}</h2>
              <p className="muted small" style={{ marginTop: 6 }}>{t('landing.demo.password')} <b className="mono">demo12345</b></p></div>
          </div>
          {error && <div className="alert error" style={{ marginTop: 14 }}>{error}</div>}
          <div className="grid grid-3" style={{ marginTop: 18 }}>
            {DEMO.map((d) => (
              <div key={d.email} className="card flat" style={{ background: 'var(--surface-2)' }}>
                <div className="demo-acc">
                  <span className="avatar">{d.role === 'candidate' ? <UserRound size={20} /> : <Building2 size={20} />}</span>
                  <div><div className="bold">{t(`landing.demo.${d.key}.title` as MessageKey)}</div><div className="tiny muted mono">{d.email}</div></div>
                </div>
                <p className="small muted" style={{ margin: '10px 0 14px', minHeight: 40 }}>{t(`landing.demo.${d.key}.text` as MessageKey)}</p>
                <button className="btn block" disabled={busy !== null} onClick={() => demoLogin(d.email)}>
                  {busy === d.email ? t('landing.demo.signingIn') : t('landing.demo.signIn')}</button>
              </div>
            ))}
          </div>
        </div>
        <p className="center tiny muted" style={{ marginTop: 28 }}>{t('landing.footer')} <a href="/api/docs">/api/docs</a></p>
      </section>
    </div>
  )
}
