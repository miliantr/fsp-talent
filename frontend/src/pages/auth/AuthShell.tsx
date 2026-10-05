import { BadgeCheck, Handshake, Trophy } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from '../../components/AppLayout'
import { LanguageSwitcher } from '../../components/LanguageSwitcher'
import { useI18n } from '../../i18n/context'

export function AuthShell({ children }: { children: ReactNode }) {
  const { t } = useI18n()
  return (
    <div className="auth-wrap">
      <div className="auth-side">
        <div className="row between">
          <Link to="/" className="brand"><span className="brand-mark"><Logo /></span><span className="brand-name">FSP Talent</span></Link>
          <LanguageSwitcher tone="light" />
        </div>
        <div>
          <h1 style={{ fontSize: 34 }}>{t('auth.side.title')}</h1>
          <div className="stack" style={{ marginTop: 28, gap: 16 }}>
            <div className="row"><BadgeCheck /> {t('auth.side.category')}</div>
            <div className="row"><Trophy /> {t('auth.side.fsp')}</div>
            <div className="row"><Handshake /> {t('auth.side.employer')}</div>
          </div>
        </div>
        <p className="tiny" style={{ opacity: 0.7 }}>{t('auth.side.law')}</p>
      </div>
      <div className="auth-main"><div className="auth-card">{children}</div></div>
    </div>
  )
}
