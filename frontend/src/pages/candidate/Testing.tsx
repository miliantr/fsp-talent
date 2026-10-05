import { ArrowRight, Clock, Lock, PlayCircle, RefreshCcw, ShieldCheck, Shuffle, Sigma } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { Attempt, CandidateProfile, Eligibility, TestingStatus } from '../../api/types'
import { CategoryBadge, ErrorBox, Loading, OutcomeBadge, useToast } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'
import { useReference } from '../../lib/reference'

export default function TestingPage() {
  const nav = useNavigate()
  const toast = useToast()
  const { t, fmt } = useI18n()
  const { ref, specName, gradeName } = useReference()
  const profile = useApi<CandidateProfile>('/candidate/profile')
  const [spec, setSpec] = useState<string>('')
  const [grade, setGrade] = useState<string>('')
  const status = useApi<TestingStatus>(spec ? '/candidate/testing' : null, { specialization_id: spec })
  const [busy, setBusy] = useState<string | null>(null)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (profile.data) {
      setSpec(profile.data.specialization_id ?? profile.data.category?.specialization_id ?? 'backend')
      setGrade(profile.data.declared_grade_id ?? '')
    }
  }, [profile.data])

  if (profile.loading && !profile.data) return <Loading />
  if (profile.error) return <ErrorBox error={profile.error} />
  const p = profile.data
  if (!p) return null
  const surveyDone = Boolean(p.specialization_id && p.declared_grade_id)
  const s = status.data

  const saveSurvey = async () => {
    setBusy('survey')
    setErr(null)
    try {
      profile.setData(await api<CandidateProfile>('/candidate/profile', { method: 'PUT', body: { specialization_id: spec, declared_grade_id: grade } }))
      toast(t('test.surveySaved'))
      await status.reload()
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setBusy(null)
    }
  }

  const start = async (e: Eligibility) => {
    setBusy(e.grade)
    setErr(null)
    try {
      if (!surveyDone || p.specialization_id !== spec) {
        await api('/candidate/profile', { method: 'PUT', body: { specialization_id: spec, declared_grade_id: grade || e.grade } })
      }
      const att = await api<Attempt>('/candidate/testing/start', { method: 'POST', body: { specialization_id: spec, target_grade: e.grade } })
      nav(`/candidate/testing/${att.id}`)
    } catch (ex) {
      setErr(ex instanceof ApiError && ex.code === 'cooldown' ? ex.message : errorMessage(ex))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{t('nav.testing')}</h1><p className="sub">{t('test.sub')}</p></div>
        <CategoryBadge category={p.category} size="lg" />
      </div>
      <ErrorBox error={err} />

      {s?.active_attempt && (
        <div className="alert violet" style={{ alignItems: 'center' }}>
          <Clock size={18} /><div style={{ flex: 1 }}>{t('test.active', {
            spec: specName(s.active_attempt.specialization_id), grade: gradeName(s.active_attempt.target_grade),
            answered: s.active_attempt.answered, total: s.active_attempt.total, time: fmt.time(s.active_attempt.deadline_at),
          })}</div>
          <Link className="btn sm" to={`/candidate/testing/${s.active_attempt.id}`}>{t('test.continue')}</Link>
        </div>
      )}

      <div className="split">
        <div className="stack-lg">
          <div className="card stack-lg">
            <div className="card-title" style={{ marginBottom: 0 }}><h3><span className="step-num">1</span>{t('test.survey')}</h3>
              {surveyDone && <span className="badge success">{t('test.surveyDone')}</span>}</div>
            <div className="field"><label>{t('cand.profile.industry')}</label><div className="chip on" style={{ width: 'fit-content' }}>{t('cand.profile.industryIt')}</div></div>
            <div className="field"><label>{t('cand.profile.spec')}</label>
              <div className="grid grid-4">
                {ref?.specializations.map((sp) => (
                  <button key={sp.id} type="button" className={`option ${spec === sp.id ? 'on' : ''}`} onClick={() => setSpec(sp.id)} style={{ flexDirection: 'column', gap: 4 }}>
                    <b>{sp.name}</b><span className="tiny muted" style={{ fontWeight: 500 }}>{sp.description}</span></button>
                ))}
              </div></div>
            <div className="field"><label>{t('cand.profile.declaredGrade')}</label>
              <div className="grid grid-3">
                {ref?.grades.map((g) => (
                  <button key={g.id} type="button" className={`option ${grade === g.id ? 'on' : ''}`} onClick={() => setGrade(g.id)} style={{ flexDirection: 'column', gap: 4 }}>
                    <b>{g.name}</b><span className="tiny muted" style={{ fontWeight: 500 }}>{g.description}</span></button>
                ))}
              </div></div>
            <div className="row"><button className="btn secondary" onClick={saveSurvey} disabled={!spec || !grade || busy === 'survey'}>{t('test.saveSurvey')}</button></div>
          </div>

          <div className="card">
            <div className="card-title"><h3><span className="step-num">2</span>{t('test.gradeTest', { spec: specName(spec) })}</h3>
              <button className="icon-btn" onClick={() => status.reload()} aria-label={t('common.refresh')}><RefreshCcw size={16} /></button></div>
            {status.loading && !s ? <Loading /> : status.error ? <ErrorBox error={status.error} /> : s && (
              <div className="grid grid-3">
                {s.eligibility.map((e) => {
                  const declared = e.grade === grade
                  return (
                    <div key={e.grade} className="card flat" style={{ borderColor: declared ? 'var(--primary)' : undefined, borderWidth: declared ? 2 : 1 }}>
                      <div className="row between"><h3>{e.grade_name}</h3>{declared && <span className="badge violet">{t('test.declared')}</span>}</div>
                      <p className="small muted" style={{ margin: '6px 0 12px', minHeight: 40 }}>{e.allowed ? t(`test.kind.${e.kind}` as MessageKey) : e.reason}</p>
                      {e.allowed ? (
                        <button className="btn block" disabled={busy !== null || !!s.active_attempt} onClick={() => start(e)}>
                          <PlayCircle size={16} />{busy === e.grade ? t('test.generating') : t('test.start')}</button>
                      ) : (
                        <button className="btn ghost block" disabled><Lock size={14} />{e.available_at ? t('test.from', { date: fmt.shortDate(e.available_at) }) : t('test.unavailable')}</button>
                      )}
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          <div className="card">
            <div className="card-title"><h3>{t('test.history')}</h3></div>
            {!s || s.history.length === 0 ? <p className="small muted">{t('test.noAttempts')}</p> : (
              <div className="table-wrap"><table className="table">
                <thead><tr><th>{t('cand.jobs.col.date')}</th><th>{t('cand.profile.spec')}</th><th>{t('test.col.target')}</th><th>{t('test.col.score')}</th>
                  <th>{t('test.col.outcome')}</th><th /></tr></thead>
                <tbody>{s.history.map((h) => (
                  <tr key={h.attempt_id}><td>{fmt.date(h.created_at)}</td><td>{specName(h.specialization_id)}</td><td>{gradeName(h.target_grade)}</td>
                    <td className="bold">{h.scaled_score}</td><td><OutcomeBadge outcome={h.outcome} /></td>
                    <td><Link to={`/candidate/results/${h.attempt_id}`} className="small">{t('test.result')} <ArrowRight size={12} /></Link></td></tr>
                ))}</tbody></table></div>
            )}
          </div>
        </div>

        <div className="stack-lg sticky">
          <div className="card stack">
            <h3>{t('test.how')}</h3>
            <div className="row" style={{ alignItems: 'flex-start' }}><Shuffle size={18} color="var(--primary)" style={{ flex: 'none', marginTop: 2 }} />
              <span className="small">{t('test.how.blueprint')}</span></div>
            <div className="row" style={{ alignItems: 'flex-start' }}><Sigma size={18} color="var(--primary)" style={{ flex: 'none', marginTop: 2 }} />
              <span className="small">{t('test.how.irt')}</span></div>
            <div className="row" style={{ alignItems: 'flex-start' }}><ShieldCheck size={18} color="var(--primary)" style={{ flex: 'none', marginTop: 2 }} />
              <span className="small">{t('test.how.leak')}</span></div>
          </div>
          {s && (
            <div className="card stack small">
              <h3>{t('test.rules')}</h3>
              <div>• {t('test.rules.length', { n: s.rules.test_length, minutes: s.rules.time_limit_minutes })}</div>
              <div>• {t('test.rules.retake', { n: s.rules.retake_cooldown_days })}</div>
              <div>• {t('test.rules.change', { n: s.rules.grade_change_cooldown_days })}</div>
              <div>• {t('test.rules.fallback')}</div>
              <div>• {t('test.rules.upgrade')}</div>
              {s.grade_locked_until && <div className="badge violet" style={{ marginTop: 6, width: 'fit-content' }}>{t('test.locked', { date: fmt.date(s.grade_locked_until) })}</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
