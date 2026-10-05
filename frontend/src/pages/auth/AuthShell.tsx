import { BadgeCheck, Handshake, Trophy } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Logo } from '../../components/AppLayout'

export function AuthShell({ children }: { children: ReactNode }) {
  return (
    <div className="auth-wrap">
      <div className="auth-side">
        <Link to="/" className="brand"><span className="brand-mark"><Logo /></span><span className="brand-name">FSP Talent</span></Link>
        <div>
          <h1 style={{ fontSize: 34 }}>Подтверждённый профиль вместо резюме, которое никто не читает</h1>
          <div className="stack" style={{ marginTop: 28, gap: 16 }}>
            <div className="row"><BadgeCheck /> Категория по результату теста, а не по самоописанию</div>
            <div className="row"><Trophy /> Достижения ФСП подтягиваются автоматически</div>
            <div className="row"><Handshake /> Работодатель приходит сам — с вакансией и зарплатой</div>
          </div>
        </div>
        <p className="tiny" style={{ opacity: 0.7 }}>Данные обрабатываются в соответствии с 152-ФЗ</p>
      </div>
      <div className="auth-main"><div className="auth-card">{children}</div></div>
    </div>
  )
}
