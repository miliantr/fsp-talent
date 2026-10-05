import { ArrowRight, Award, CheckCircle2, CircleAlert, RotateCcw, TrendingUp } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { TestResult } from '../../api/types'
import { CompetencyBars, ErrorBox, Loading, OutcomeBadge, ScoreRing, ScoreScale } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { useReference } from '../../lib/reference'

export default function TestResultPage() {
  const { attemptId } = useParams()
  const { t, fmt } = useI18n()
  const { specName, gradeName } = useReference()
  const { data: r, error, loading } = useApi<TestResult>(`/candidate/testing/results/${attemptId}`)
  if (loading && !r) return <Loading label={t('test.result.counting')} />
  if (error) return <ErrorBox error={error} />
  if (!r) return null
  const ok = r.passed
  const icon = ok ? <CheckCircle2 size={34} /> : <CircleAlert size={34} />
  const headline = ok ? t('test.result.passed') : r.outcome === 'needs_confirmation' ? t('test.result.confirm') : t('test.result.notPassed')

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{t('test.result.title')}</h1>
          <p className="sub">{t('test.result.sub', { spec: specName(r.specialization_id), grade: gradeName(r.target_grade), date: fmt.date(r.created_at), answered: r.answered, total: r.total })}</p></div>
        <OutcomeBadge outcome={r.outcome} />
      </div>

      <div className="card" style={{ padding: 28, background: ok ? 'var(--brand-gradient)' : '#fff', color: ok ? '#fff' : 'var(--text)', border: ok ? 'none' : undefined }}>
        <div className="row between wrap" style={{ gap: 24 }}>
          <div className="stack" style={{ gap: 10, maxWidth: 620 }}>
            <div className="row" style={{ color: ok ? '#fff' : 'var(--warning)' }}>{icon}<h2 style={{ fontSize: 24 }}>{headline}</h2></div>
            {r.category_label && <span className="category lg" style={{ background: 'rgba(255,255,255,.18)', width: 'fit-content' }}><span className="ok"><Award size={18} /></span>{r.category_label}</span>}
            <p style={{ opacity: ok ? 0.9 : 1 }}>{r.recommendation}</p>
            {r.grade_changed && <span className="badge" style={{ background: 'rgba(255,255,255,.18)', color: 'inherit', width: 'fit-content' }}>{t('test.result.gradeUpdated')}</span>}
          </div>
          <div className="row" style={{ gap: 24 }}>
            <div className="center"><ScoreRing value={r.scaled_score} size={110} label={t('test.result.outOf')} color={ok ? '#fff' : undefined} />
              <div className="tiny" style={{ marginTop: 6, opacity: 0.8 }}>{t('cand.dash.scaledScore')}</div></div>
            <div className="center"><ScoreRing value={Math.round(r.confidence * 100)} size={110} color={ok ? '#f0b8ff' : undefined} />
              <div className="tiny" style={{ marginTop: 6, opacity: 0.8 }}>{t('test.result.confidence')}</div></div>
          </div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <h3>{t('test.result.scale')}</h3>
          <div style={{ marginTop: 12 }}><ScoreScale score={r.scaled_score} /></div>
          <div className="divider" />
          <dl className="kv small">
            <dt>{t('test.result.theta')}</dt><dd>{fmt.number(r.theta)} ± {fmt.number(r.theta_se)}</dd>
            <dt>{t('test.result.raw')}</dt><dd>{fmt.number(r.raw_percent)}%</dd>
            <dt>{t('test.result.whyDiffers')}</dt><dd style={{ fontWeight: 500 }}>{t('test.result.whyDiffersText')}</dd>
          </dl>
        </div>
        <div className="card"><h3>{t('test.result.competencies')}</h3><div style={{ marginTop: 14 }}><CompetencyBars items={r.competencies} /></div></div>
      </div>

      <div className="row wrap">
        {r.upgrade_eligible && <Link to="/candidate/testing" className="btn"><TrendingUp size={16} />{t('test.result.upgrade')}</Link>}
        {!ok && <Link to="/candidate/testing" className="btn"><RotateCcw size={16} />{r.outcome === 'needs_confirmation' ? t('test.result.takeConfirmation') : t('test.result.chooseLower')}</Link>}
        <Link to="/candidate" className="btn ghost">{t('test.result.toCabinet')} <ArrowRight size={16} /></Link>
        {ok && <Link to="/candidate/settings" className="btn secondary">{t('test.result.visibility')}</Link>}
      </div>
    </div>
  )
}
