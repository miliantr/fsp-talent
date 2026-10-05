import { ArrowRight, BadgeCheck, Building2, ClipboardCheck, Handshake, ShieldCheck, Sparkles, Trophy, UserRound } from 'lucide-react'
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, errorMessage } from '../api/client'
import type { TokenOut } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { Logo } from '../components/AppLayout'

const DEMO = [
  { email: 'candidate@demo.ru', role: 'candidate', title: 'Кандидат · Backend Middle', text: 'Подтверждённая категория, достижения ФСП, входящие приглашения' },
  { email: 'fresh@demo.ru', role: 'candidate', title: 'Кандидат без теста', text: 'Профиль заполнен — можно сразу пройти тестирование' },
  { email: 'hr@demo.ru', role: 'employer', title: 'Работодатель', text: '«Технологии Будущего»: потребности, подборки, приглашения' },
]

const FLOW = [
  { icon: <UserRound size={20} />, title: 'Опрос', text: 'Специализация и предполагаемый грейд' },
  { icon: <ClipboardCheck size={20} />, title: 'Тест на грейд', text: 'Индивидуальный вариант сопоставимой сложности' },
  { icon: <BadgeCheck size={20} />, title: 'Категория', text: '«Backend · Middle» + достижения ФСП' },
  { icon: <Sparkles size={20} />, title: 'Подборка', text: 'Работодатель описывает потребность и получает рейтинг с объяснением' },
  { icon: <Handshake size={20} />, title: 'Приглашение', text: 'С зарплатной вилкой — кандидат видит условия до начала общения' },
]

export default function Landing() {
  const { user, signIn } = useAuth()
  const nav = useNavigate()
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const demoLogin = async (email: string) => {
    setBusy(email)
    setError(null)
    try {
      const t = await api<TokenOut>('/auth/login', { method: 'POST', body: { email, password: 'demo12345' } })
      signIn(t)
      nav(t.user.role === 'candidate' ? '/candidate' : '/employer')
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
              <span><div className="brand-name">FSP Talent</div><div className="brand-sub">Федерация спортивного программирования</div></span></Link>
            <div className="row">
              {user ? (
                <Link className="btn white" to={user.role === 'candidate' ? '/candidate' : '/employer'}>Мой кабинет <ArrowRight size={16} /></Link>
              ) : (
                <><Link className="btn light" to="/login">Войти</Link><Link className="btn white" to="/register">Регистрация</Link></>
              )}
            </div>
          </div>
          <div className="pill" style={{ marginTop: 48 }}><ShieldCheck size={15} />Обратная механика подбора · верифицированные профили</div>
          <h1>Работодатель сам находит вас — по подтверждённым навыкам, а&nbsp;не&nbsp;по&nbsp;ключевым словам</h1>
          <p className="lead">Кандидат проходит тест на заявленный грейд и получает категорию. Работодатель описывает потребность,
            видит ранжированную подборку с объяснением и отправляет приглашение с зарплатой. Достижения ФСП усиливают профиль.</p>
          <div className="row wrap" style={{ marginTop: 30, gap: 12 }}>
            <Link className="btn white lg" to="/register?role=candidate"><UserRound size={18} />Я ищу работу</Link>
            <Link className="btn light lg" to="/register?role=employer"><Building2 size={18} />Я нанимаю</Link>
          </div>
        </div>
      </section>

      <section className="landing-section">
        <h2>Как это работает</h2>
        <p className="muted" style={{ marginTop: 6 }}>Инициатива у работодателя: кандидат не рассылает отклики вслепую.</p>
        <div className="flow" style={{ marginTop: 22 }}>
          {FLOW.map((f, i) => (
            <div key={f.title} className="card">
              <div className="row between"><span className="step-num">{i + 1}</span><span style={{ color: 'var(--primary)' }}>{f.icon}</span></div>
              <h3 style={{ marginTop: 14 }}>{f.title}</h3>
              <p className="small muted" style={{ marginTop: 4 }}>{f.text}</p>
            </div>
          ))}
        </div>

        <div className="grid grid-3" style={{ marginTop: 36 }}>
          <div className="card"><h3 className="row"><ClipboardCheck size={18} color="var(--primary)" />Тест, который нельзя «слить»</h3>
            <p className="small muted" style={{ marginTop: 8 }}>Варианты собираются из калиброванного банка по единому плану (blueprint),
              параметрические задания генерируют новые числа, оценка — по IRT, подозрительные паттерны требуют подтверждения.</p></div>
          <div className="card"><h3 className="row"><Sparkles size={18} color="var(--primary)" />Объяснимый матчинг</h3>
            <p className="small muted" style={{ marginTop: 8 }}>Каждый процент совпадения раскладывается на вклад факторов: стек, тест, грейд,
              ФСП, актуальность, зарплата. Видно, почему кандидат A выше кандидата B.</p></div>
          <div className="card"><h3 className="row"><Trophy size={18} color="var(--accent)" />ФСП как сигнал, а не фильтр</h3>
            <p className="small muted" style={{ marginTop: 8 }}>Достижения автоматически подтягиваются из реестра ФСП и поднимают профиль.
              Нет истории — нет штрафа: используется нейтральная база.</p></div>
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
        <div className="card" style={{ padding: 26 }}>
          <div className="row between wrap">
            <div><h2>Демо-доступ</h2><p className="muted small" style={{ marginTop: 6 }}>Пароль у всех демо-аккаунтов: <b className="mono">demo12345</b></p></div>
          </div>
          {error && <div className="alert error" style={{ marginTop: 14 }}>{error}</div>}
          <div className="grid grid-3" style={{ marginTop: 18 }}>
            {DEMO.map((d) => (
              <div key={d.email} className="card flat" style={{ background: 'var(--surface-2)' }}>
                <div className="demo-acc">
                  <span className="avatar">{d.role === 'candidate' ? <UserRound size={20} /> : <Building2 size={20} />}</span>
                  <div><div className="bold">{d.title}</div><div className="tiny muted mono">{d.email}</div></div>
                </div>
                <p className="small muted" style={{ margin: '10px 0 14px', minHeight: 40 }}>{d.text}</p>
                <button className="btn block" disabled={busy !== null} onClick={() => demoLogin(d.email)}>
                  {busy === d.email ? 'Входим…' : 'Войти в демо'}</button>
              </div>
            ))}
          </div>
        </div>
        <p className="center tiny muted" style={{ marginTop: 28 }}>FSP Talent · MVP для хакатона ФСП · API: <a href="/api/docs">/api/docs</a></p>
      </section>
    </div>
  )
}
