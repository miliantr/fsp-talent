import { ArrowRight, Building2, Inbox, Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { EmployerDashboard } from '../../api/types'
import { Empty, ErrorBox, InvitationStatusBadge, Loading } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'
import { INVITATION_STATUSES, INVITATION_TONE } from '../../lib/format'

const TONE_COLOR: Record<string, string> = {
  info: 'var(--info)', violet: 'var(--primary)', success: 'var(--success)', danger: 'var(--danger)', muted: '#c9c2d8',
}

export default function EmployerDashboardPage() {
  const { data, error, loading, reload } = useApi<EmployerDashboard>('/employer/dashboard')
  const { t, fmt } = useI18n()
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data) return null
  const inv = data.invitations

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{data.company.company_name || t('emp.dash.yourCompany')}</h1><p className="sub">{t('emp.dash.sub')}</p></div>
        <Link className="btn lg" to="/employer/requirements/new"><Plus size={18} />{t('emp.newNeed')}</Link>
      </div>
      {!data.company_complete && (
        <div className="alert warning" style={{ alignItems: 'center' }}><Building2 size={18} /><span style={{ flex: 1 }}>{t('emp.dash.fillCompany')}</span>
          <Link className="btn sm" to="/employer/company">{t('emp.dash.fill')}</Link></div>
      )}
      <div className="grid grid-4">
        <div className="card stat"><span className="k">{t('emp.dash.stat.needs')}</span><span className="v">{data.requirements_total}</span></div>
        <div className="card stat"><span className="k">{t('emp.dash.stat.invitations')}</span><span className="v">{inv.total}</span></div>
        <div className="card stat"><span className="k">{t('emp.dash.stat.accepted')}</span><span className="v" style={{ color: 'var(--success)' }}>{inv.by_status.accepted ?? 0}</span></div>
        <div className="card stat"><span className="k">{t('emp.dash.stat.conversion')}</span><span className="v">{inv.acceptance_rate != null ? `${inv.acceptance_rate}%` : '—'}</span></div>
      </div>

      <div className="card">
        <div className="card-title"><h3>{t('emp.dash.funnel')}</h3></div>
        <div className="stacked" style={{ height: 18 }}>
          {INVITATION_STATUSES.map((k) => {
            const n = inv.by_status[k] ?? 0
            return n ? <i key={k} style={{ width: `${(n / Math.max(1, inv.total)) * 100}%`, background: TONE_COLOR[INVITATION_TONE[k]] }}
              title={`${t(`status.invitation.${k}` as MessageKey)}: ${n}`} /> : null
          })}
        </div>
        <div className="legend" style={{ marginTop: 10 }}>{INVITATION_STATUSES.map((k) => <span key={k}><InvitationStatusBadge status={k} /> {inv.by_status[k] ?? 0}</span>)}</div>
      </div>

      <div className="split">
        <div className="card">
          <div className="card-title"><h3><Sparkles size={18} color="var(--primary)" />{t('nav.requirements')}</h3>
            <Link to="/employer/requirements" className="small">{t('common.all')} <ArrowRight size={13} /></Link></div>
          {data.requirements.length === 0 ? (
            <Empty title={t('emp.dash.firstNeed')} text={t('emp.dash.firstNeedExample')}
              action={<Link className="btn" to="/employer/requirements/new">{t('emp.dash.describe')}</Link>} />
          ) : (
            <div className="stack">
              {data.requirements.map((r) => (
                <Link key={r.id} to={`/employer/requirements/${r.id}`} className="card flat hover" style={{ color: 'inherit', textDecoration: 'none', padding: 14 }}>
                  <div className="row between wrap">
                    <div><div className="bold">{r.title}</div><div className="small muted">{r.specialization_name} · {r.grade_name} · {fmt.salaryRange(r.salary_from, r.salary_to)}</div></div>
                    <div className="row"><span className="badge violet">{t('emp.inShortlist', { n: r.stats?.matched ?? 0 })}</span>
                      {r.stats?.top_percent != null && <span className="badge success">{t('emp.dash.top', { pct: r.stats.top_percent })}</span>}</div>
                  </div>
                </Link>
              ))}
            </div>
          )}
        </div>
        <div className="card">
          <div className="card-title"><h3><Inbox size={18} color="var(--primary)" />{t('emp.dash.recent')}</h3><Link to="/employer/invitations" className="small">{t('common.all')}</Link></div>
          {data.recent_responses.length === 0 ? <p className="small muted">{t('emp.dash.noResponses')}</p> : (
            <div className="stack">
              {data.recent_responses.map((i) => (
                <div key={i.id} className="stack" style={{ gap: 2, paddingBottom: 10, borderBottom: '1px solid var(--border)' }}>
                  <div className="row between"><b className="small">{i.candidate.display_name}</b><InvitationStatusBadge status={i.status} /></div>
                  <span className="tiny muted">{i.position_title} · {fmt.ago(i.responded_at)}</span>
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
