import { Plus, Sparkles } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { Requirement } from '../../api/types'
import { Empty, ErrorBox, Loading } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { workFormatKey } from '../../lib/format'

export default function Requirements() {
  const { data, error, loading, reload } = useApi<Requirement[]>('/employer/requirements')
  const { t, fmt } = useI18n()
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const items = data ?? []
  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.requirements')}</h1><p className="sub">{t('emp.reqs.sub')}</p></div>
        <Link className="btn lg" to="/employer/requirements/new"><Plus size={18} />{t('emp.newNeed')}</Link></div>
      {items.length === 0 ? (
        <div className="card"><Empty icon={<Sparkles size={26} />} title={t('emp.reqs.emptyTitle')} text={t('emp.reqs.emptyText')}
          action={<Link className="btn" to="/employer/requirements/new">{t('emp.reqs.describe')}</Link>} /></div>
      ) : (
        <div className="grid grid-2">
          {items.map((r) => (
            <Link key={r.id} to={`/employer/requirements/${r.id}`} className="card hover stack" style={{ color: 'inherit', textDecoration: 'none' }}>
              <div className="row between"><span className="badge violet">{r.specialization_name} · {r.grade_name}</span>
                <span className="row">{r.is_public && <span className="badge success">{t('emp.reqs.vacancy')}</span>}
                  {r.status === 'closed' && <span className="badge muted">{t('emp.reqs.closed')}</span>}</span></div>
              <h2 style={{ fontSize: 18 }}>{r.title}</h2>
              <div className="small muted">{fmt.salaryRange(r.salary_from, r.salary_to)} · {t(workFormatKey(r.work_format))} · {fmt.ago(r.created_at)}</div>
              <div className="row wrap">{r.skills.slice(0, 6).map((s) => <span key={s.slug} className={`chip ${s.importance === 'must' ? 'on' : ''}`}>{s.name}</span>)}</div>
              <div className="divider" style={{ margin: '4px 0' }} />
              <div className="row wrap small">
                <span>{t('emp.reqs.matched', { n: r.stats?.matched ?? 0 })}</span>
                {r.stats?.top_percent != null && <span>· {t('emp.reqs.best', { pct: r.stats.top_percent })}</span>}
                <span>· {t('emp.reqs.invited', { n: r.stats?.invited ?? 0 })}</span><span>· {t('emp.reqs.accepted', { n: r.stats?.accepted ?? 0 })}</span>
                {r.is_public && <span>· {t('emp.reqs.applications', { n: r.stats?.applications ?? 0 })}</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
