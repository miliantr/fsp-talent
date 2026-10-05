import { Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { Requirement } from '../../api/types'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { ago, salaryRange, WORK_FORMAT } from '../../lib/format'

export default function Requirements() {
  const { data, error, loading, reload } = useApi<Requirement[]>('/employer/requirements')
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const items = data ?? []
  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>Потребности и подборки</h1>
        <p className="sub">Каждая потребность — сохранённая подборка кандидатов. Публиковать вакансию не обязательно: приглашать можно напрямую.</p></div>
        <Link className="btn lg" to="/employer/requirements/new"><Plus size={18} />Новая потребность</Link></div>
      {items.length === 0 ? (
        <div className="card"><Empty icon={<Sparkles size={26} />} title="Потребностей пока нет" text="Опишите, кого ищете, — подборка сформируется сразу."
          action={<Link className="btn" to="/employer/requirements/new">Описать потребность</Link>} /></div>
      ) : (
        <div className="grid grid-2">
          {items.map((r) => (
            <Link key={r.id} to={`/employer/requirements/${r.id}`} className="card hover stack" style={{ color: 'inherit', textDecoration: 'none' }}>
              <div className="row between"><span className="badge violet">{r.specialization_name} · {r.grade_name}</span>
                <span className="row">{r.is_public && <span className="badge success">вакансия</span>}{r.status === 'closed' && <span className="badge muted">закрыта</span>}</span></div>
              <h2 style={{ fontSize: 18 }}>{r.title}</h2>
              <div className="small muted">{salaryRange(r.salary_from, r.salary_to)} · {WORK_FORMAT[r.work_format]} · {ago(r.created_at)}</div>
              <div className="row wrap">{r.skills.slice(0, 6).map((s) => <span key={s.slug} className={`chip ${s.importance === 'must' ? 'on' : ''}`}>{s.name}</span>)}</div>
              <div className="divider" style={{ margin: '4px 0' }} />
              <div className="row wrap small">
                <span><b>{r.stats?.matched ?? 0}</b> в подборке</span>
                {r.stats?.top_percent != null && <span>· лучший <b>{r.stats.top_percent}%</b></span>}
                <span>· приглашено <b>{r.stats?.invited ?? 0}</b></span><span>· приняли <b>{r.stats?.accepted ?? 0}</b></span>
                {r.is_public && <span>· откликов <b>{r.stats?.applications ?? 0}</b></span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
