import { ArrowRight, Building2, Inbox, Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { EmployerDashboard } from '../../api/types'
import { Empty, ErrorBox, InvitationStatusBadge, Loading } from '../../components/ui'
import { ago, INVITATION_STATUS, salaryRange } from '../../lib/format'

export default function EmployerDashboardPage() {
  const { data, error, loading, reload } = useApi<EmployerDashboard>('/employer/dashboard')
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data) return null
  const inv = data.invitations

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{data.company.company_name || 'Ваша компания'}</h1><p className="sub">Опишите потребность — получите ранжированную подборку подтверждённых кандидатов и пригласите лучших с зарплатной вилкой.</p></div>
        <Link className="btn lg" to="/employer/requirements/new"><Plus size={18} />Новая потребность</Link>
      </div>
      {!data.company_complete && (
        <div className="alert warning" style={{ alignItems: 'center' }}><Building2 size={18} /><span style={{ flex: 1 }}>Заполните профиль компании — кандидаты видят его в приглашениях.</span>
          <Link className="btn sm" to="/employer/company">Заполнить</Link></div>
      )}
      <div className="grid grid-4">
        <div className="card stat"><span className="k">Потребностей</span><span className="v">{data.requirements_total}</span></div>
        <div className="card stat"><span className="k">Приглашений</span><span className="v">{inv.total}</span></div>
        <div className="card stat"><span className="k">Принято</span><span className="v" style={{ color: 'var(--success)' }}>{inv.by_status.accepted ?? 0}</span></div>
        <div className="card stat"><span className="k">Конверсия ответов</span><span className="v">{inv.acceptance_rate != null ? `${inv.acceptance_rate}%` : '—'}</span></div>
      </div>

      <div className="card">
        <div className="card-title"><h3>Воронка приглашений</h3></div>
        <div className="stacked" style={{ height: 18 }}>
          {Object.entries(INVITATION_STATUS).map(([k, v]) => {
            const n = inv.by_status[k] ?? 0
            const color = { info: 'var(--info)', violet: 'var(--primary)', success: 'var(--success)', danger: 'var(--danger)', muted: '#c9c2d8' }[v.tone]
            return n ? <i key={k} style={{ width: `${(n / Math.max(1, inv.total)) * 100}%`, background: color }} title={`${v.label}: ${n}`} /> : null
          })}
        </div>
        <div className="legend" style={{ marginTop: 10 }}>{Object.keys(INVITATION_STATUS).map((k) => <span key={k}><InvitationStatusBadge status={k} /> {inv.by_status[k] ?? 0}</span>)}</div>
      </div>

      <div className="split">
        <div className="card">
          <div className="card-title"><h3><Sparkles size={18} color="var(--primary)" />Потребности и подборки</h3><Link to="/employer/requirements" className="small">Все <ArrowRight size={13} /></Link></div>
          {data.requirements.length === 0 ? (
            <Empty title="Опишите первую потребность" text="Например: Backend Middle, Python, FastAPI, PostgreSQL, 180–250 тыс. ₽" action={<Link className="btn" to="/employer/requirements/new">Описать</Link>} />
          ) : (
            <div className="stack">
              {data.requirements.map((r) => (
                <Link key={r.id} to={`/employer/requirements/${r.id}`} className="card flat hover" style={{ color: 'inherit', textDecoration: 'none', padding: 14 }}>
                  <div className="row between wrap">
                    <div><div className="bold">{r.title}</div><div className="small muted">{r.specialization_name} · {r.grade_name} · {salaryRange(r.salary_from, r.salary_to)}</div></div>
                    <div className="row"><span className="badge violet">{r.stats?.matched ?? 0} в подборке</span>{r.stats?.top_percent != null && <span className="badge success">топ {r.stats.top_percent}%</span>}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="card">
          <div className="card-title"><h3><Inbox size={18} color="var(--primary)" />Последние ответы</h3><Link to="/employer/invitations" className="small">Все</Link></div>
          {data.recent_responses.length === 0 ? <p className="small muted">Ответов пока нет.</p> : (
            <div className="stack">
              {data.recent_responses.map((i) => (
                <div key={i.id} className="stack" style={{ gap: 2, paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
                  <div className="row between"><b className="small">{i.candidate.display_name}</b><InvitationStatusBadge status={i.status} /></div>
                  <span className="tiny muted">{i.position_title} · {ago(i.responded_at)}</span>
                  {i.contacts && <span className="tiny">✉ {i.contacts.email}{i.contacts.telegram ? ` · ${i.contacts.telegram}` : ''}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
