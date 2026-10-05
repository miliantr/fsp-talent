import { ArrowRight, CheckCircle2, Circle, Eye, EyeOff, Inbox, Lock, Trophy } from 'lucide-react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { CandidateDashboard } from '../../api/types'
import {
  CategoryBadge,
  Empty,
  ErrorBox,
  FspSummary,
  InvitationStatusBadge,
  Loading,
  OutcomeBadge,
  ScoreRing,
  ScoreScale,
} from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { workFormatKey } from '../../lib/format'
import { useReference } from '../../lib/reference'

export default function CandidateDashboardPage() {
  const { gradeName } = useReference()
  const { t, fmt } = useI18n()
  const { data, error, loading, reload } = useApi<CandidateDashboard>('/candidate/dashboard')
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data) return null
  const p = data.profile
  const cat = p.category

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{t('cand.dash.title', { name: p.first_name || t('cand.dash.nameFallback') })}</h1>
          <p className="sub">{t('cand.dash.sub')}</p></div>
        <Link className="btn ghost" to="/candidate/print">{t('cand.dash.pdf')}</Link>
      </div>

      <div className="card" style={{ background: 'var(--brand-gradient)', color: '#fff', border: 'none', padding: 26 }}>
        <div className="row between wrap" style={{ gap: 24, alignItems: 'flex-start' }}>
          <div className="stack" style={{ gap: 12, minWidth: 280 }}>
            <span className="tiny" style={{ opacity: 0.75, textTransform: 'uppercase', letterSpacing: '.08em', fontWeight: 700 }}>{t('cand.dash.currentCategory')}</span>
            {cat ? (
              <span className="category lg" style={{ background: 'rgba(255,255,255,.16)' }}><span className="ok"><CheckCircle2 size={18} /></span>{cat.label}</span>
            ) : (
              <span className="category lg" style={{ background: 'rgba(255,255,255,.12)' }}><span className="ok"><Lock size={16} /></span>{t('cand.dash.notVerified')}</span>
            )}
            <div className="small" style={{ opacity: 0.85 }}>
              {cat ? t('cand.dash.verifiedAt', {
                date: fmt.date(cat.verified_at),
                when: cat.upgrade_eligible ? t('cand.dash.changeNow') : t('cand.dash.changeAfter', { date: fmt.date(cat.locked_until) }),
              }) : t('cand.dash.verifyHint')}
            </div>
            <div className="row wrap">
              <span className="badge" style={{ background: 'rgba(255,255,255,.15)', color: '#fff' }}>
                {data.searchable ? <><Eye size={13} />{t('cand.dash.visible')}</> : <><EyeOff size={13} />{t('cand.dash.hidden')}</>}
              </span>
              {p.fsp.available
                ? <span className="badge" style={{ background: 'rgba(255,255,255,.15)', color: '#fff' }}><Trophy size={13} />{t('cand.dash.fspCount', { n: p.fsp.count })}</span>
                : <span className="badge" style={{ background: 'rgba(255,255,255,.1)', color: '#fff' }}>{t('fsp.noHistory')}</span>}
            </div>
          </div>
          <div className="row wrap" style={{ gap: 14 }}>
            <div className="center"><ScoreRing value={cat?.scaled_score ?? 0} size={84} label={t('cand.dash.points')} color="#fff" />
              <div className="tiny" style={{ opacity: 0.8, marginTop: 6 }}>{t('cand.dash.scaledScore')}</div></div>
            <div className="center"><ScoreRing value={Math.round((cat?.confidence ?? 0) * 100)} size={84} color="#f0b8ff" />
              <div className="tiny" style={{ opacity: 0.8, marginTop: 6 }}>{t('cand.dash.confidence')}</div></div>
            <div className="center"><ScoreRing value={p.completeness.percent} size={84} color="#9fe6c4" />
              <div className="tiny" style={{ opacity: 0.8, marginTop: 6 }}>{t('cand.dash.completeness')}</div></div>
          </div>
        </div>
        {cat?.scaled_score != null && (
          <div style={{ marginTop: 20, background: 'rgba(255,255,255,.95)', borderRadius: 14, padding: '12px 16px 10px', color: 'var(--text)' }}>
            <ScoreScale score={cat.scaled_score} />
          </div>
        )}
      </div>

      <div className="split">
        <div className="stack-lg">
          <div className="card">
            <div className="card-title"><h3><Inbox size={18} color="var(--primary)" />{t('cand.dash.invitations')}</h3>
              <Link to="/candidate/invitations" className="small">{t('cand.dash.all', { n: data.invitations.total })} <ArrowRight size={13} /></Link></div>
            {data.invitations.latest.length === 0 ? (
              <Empty title={t('cand.dash.noInvitations')} text={data.searchable ? t('cand.dash.noInvitationsVisible') : t('cand.dash.noInvitationsHidden')} />
            ) : (
              <div className="stack">
                {data.invitations.latest.map((i) => (
                  <Link key={i.id} to={`/candidate/invitations/${i.id}`} className="card flat hover" style={{ color: 'inherit', textDecoration: 'none', padding: 16 }}>
                    <div className="row between wrap">
                      <div><div className="bold">{i.position_title}</div>
                        <div className="small muted">{i.company.name} · {t(workFormatKey(i.work_format))} · {fmt.ago(i.created_at)}</div></div>
                      <div className="row"><span className="salary" style={{ fontSize: 17 }}>{fmt.salaryRange(i.salary_from, i.salary_to)}</span><InvitationStatusBadge status={i.status} /></div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {p.competencies.length > 0 && (
            <div className="card">
              <div className="card-title"><h3>{t('cand.dash.competencies')}</h3><Link to="/candidate/testing" className="small">{t('nav.testing')}</Link></div>
              <div className="grid grid-2">
                {p.competencies.map((c) => (
                  <div key={c.id}><div className="row between small"><span>{c.name}</span><b>{c.score}%</b></div>
                    <div className="bar" style={{ marginTop: 4 }}><i style={{ width: `${c.score}%` }} /></div></div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="stack-lg">
          <div className="card">
            <h3>{t('cand.dash.path')}</h3>
            <div className="stack" style={{ marginTop: 12 }}>
              {data.steps.map((s) => (
                <Link key={s.key} to={s.link} className="row" style={{ color: s.done ? 'var(--muted)' : 'var(--text)', textDecoration: 'none' }}>
                  {s.done ? <CheckCircle2 size={20} color="var(--success)" /> : <Circle size={20} color="var(--border-strong)" />}
                  <span style={{ textDecoration: s.done ? 'line-through' : 'none' }}>{s.title}</span>
                </Link>
              ))}
            </div>
          </div>
          <div className="card">
            <div className="card-title"><h3>{t('cand.dash.lastTest')}</h3></div>
            {data.last_result ? (
              <div className="stack">
                <OutcomeBadge outcome={data.last_result.outcome} />
                <div className="small muted">{t('cand.dash.target', { grade: gradeName(data.last_result.target_grade), date: fmt.date(data.last_result.created_at) })}</div>
                <div className="row"><b style={{ fontSize: 22, fontFamily: 'var(--display)' }}>{data.last_result.scaled_score}</b><span className="muted">/ 100</span></div>
                <Link className="btn secondary sm" to={`/candidate/results/${data.last_result.attempt_id}`}>{t('cand.dash.details')}</Link>
              </div>
            ) : (
              <div className="stack"><p className="small muted">{t('cand.dash.noTest')}</p><Link className="btn" to="/candidate/testing">{t('cand.dash.takeTest')}</Link></div>
            )}
          </div>
          <div className="card">
            <div className="card-title"><h3>{t('cand.dash.profile')}</h3><Link to="/candidate/profile" className="small">{t('cand.dash.edit')}</Link></div>
            <CategoryBadge category={cat} />
            <div className="row wrap" style={{ marginTop: 12 }}><FspSummary fsp={p.fsp} /></div>
            {p.completeness.missing.length > 0 && (
              <><div className="divider" /><div className="small muted">{t('cand.dash.missing')}</div>
                <ul className="small" style={{ margin: '6px 0 0', paddingLeft: 18 }}>{p.completeness.missing.slice(0, 5).map((m) => <li key={m.key}>{m.title}</li>)}</ul></>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
