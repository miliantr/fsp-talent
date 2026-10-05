import { Link2, Lock, ShieldCheck } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { CandidateProfile, CandidateSettings } from '../../api/types'
import { ErrorBox, Loading, Switch, useToast } from '../../components/ui'
import { date } from '../../lib/format'
import { useState } from 'react'

export default function SettingsPage() {
  const s = useApi<CandidateSettings>('/candidate/settings')
  const p = useApi<CandidateProfile>('/candidate/profile')
  const toast = useToast()
  const [err, setErr] = useState<string | null>(null)

  if ((s.loading && !s.data) || (p.loading && !p.data)) return <Loading />
  if (s.error) return <ErrorBox error={s.error} />
  if (!s.data || !p.data) return null
  const st = s.data

  const update = async (patch: Record<string, boolean>) => {
    setErr(null)
    try {
      s.setData(await api<CandidateSettings>('/candidate/settings', { method: 'PUT', body: patch }))
      toast('Настройки сохранены')
    } catch (e) {
      setErr(errorMessage(e))
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>Настройки</h1><p className="sub">Приватность, согласия на обработку и публикацию данных (152-ФЗ), связь с ФСП ID.</p></div></div>
      <ErrorBox error={err} />
      <div className={`alert ${st.searchable ? 'success' : 'warning'}`}>
        {st.searchable ? <ShieldCheck size={18} /> : <Lock size={18} />}
        <span>{st.searchable ? 'Ваш профиль участвует в подборках работодателей.' :
          'Профиль не виден работодателям: нужна подтверждённая категория, согласие на публикацию и включённый поиск предложений.'}</span>
      </div>
      <div className="grid grid-2">
        <div className="card">
          <h3>Видимость для работодателей</h3>
          <div className="divider" />
          <Switch checked={st.open_to_offers} onChange={(v) => update({ open_to_offers: v })} label="Открыт к предложениям" hint="Участвовать в подборках и получать приглашения" />
          <Switch checked={st.show_full_name} onChange={(v) => update({ show_full_name: v })} label="Показывать фамилию до контакта" hint="По умолчанию работодатель видит «Имя Ф.»" />
          <Switch checked={st.show_fsp} onChange={(v) => update({ show_fsp: v })} label="Показывать достижения ФСП" hint="Если выключить — ФСП не используется и в ранжировании" />
          <Switch checked={st.show_salary} onChange={(v) => update({ show_salary: v })} label="Показывать зарплатные ожидания" />
          <p className="small muted" style={{ marginTop: 10 }}>Контакты (e-mail, телефон, Telegram) не видны никогда — до принятия приглашения или вашего отклика.</p>
        </div>
        <div className="stack-lg">
          <div className="card">
            <h3>Согласия</h3>
            <div className="divider" />
            <div className="row between" style={{ padding: '10px 0' }}><span><span className="bold">Обработка персональных данных</span>
              <span className="small muted" style={{ display: 'block' }}>Дано при регистрации {date(st.consent_processing_at)}</span></span><span className="badge success">дано</span></div>
            <Switch checked={st.consent_publication_at !== null} onChange={(v) => update({ consent_publication: v })}
              label="Публикация профиля для работодателей" hint={st.consent_publication_at ? `Дано ${date(st.consent_publication_at)}` : 'Без него профиль не участвует в поиске'} />
          </div>
          <div className="card">
            <h3>ФСП ID</h3>
            <p className="small muted" style={{ marginTop: 6 }}>{p.data.fsp_id ? <>Привязан: <b className="mono">{p.data.fsp_id}</b></> : 'Не привязан. Можно привязать в любой момент.'}</p>
            <Link className="btn secondary sm" style={{ marginTop: 12 }} to="/candidate/fsp"><Link2 size={14} />Управлять</Link>
          </div>
          <div className="card"><h3>Учётная запись</h3><p className="small muted" style={{ marginTop: 6 }}>{p.data.email}</p></div>
        </div>
      </div>
    </div>
  )
}
