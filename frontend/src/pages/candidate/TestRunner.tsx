import { Check, ChevronLeft, ChevronRight, Clock, Flag } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, ApiError, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { AnswerOut, Attempt, TestResult } from '../../api/types'
import { ErrorBox, Loading, Modal, RichText } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { useReference } from '../../lib/reference'

type AnswerVal = (number | string)[]

export default function TestRunner() {
  const { attemptId } = useParams()
  const nav = useNavigate()
  const { t } = useI18n()
  const { specName, gradeName } = useReference()
  // the question texts come from the server in the UI language; switching it mid-test re-fetches the same
  // questions translated (same options in the same order, so given answers stay valid)
  const { data, error, loading } = useApi<Attempt>(`/candidate/testing/attempts/${attemptId}`)
  const [idx, setIdx] = useState(0)
  const [answers, setAnswers] = useState<Record<number, AnswerVal>>({})
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  const [finishing, setFinishing] = useState(false)
  const [now, setNow] = useState(() => Date.now())
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    if (!data) return
    if (data.status !== 'in_progress') {
      nav(`/candidate/results/${data.id}`, { replace: true })
      return
    }
    setOffset(new Date(data.server_time).getTime() - Date.now())
    setAnswers((prev) => ({ ...Object.fromEntries(data.items.filter((i) => i.answer).map((i) => [i.id, i.answer as AnswerVal])), ...prev }))
    const timer = window.setInterval(() => setNow(Date.now()), 1000)
    return () => window.clearInterval(timer)
  }, [data, nav])

  const remaining = useMemo(() => {
    if (!data) return 0
    return Math.max(0, Math.floor((new Date(data.deadline_at).getTime() - (now + offset)) / 1000))
  }, [data, now, offset])

  if (loading && !data) return <Loading label={t('test.run.loading')} />
  if (error) return <ErrorBox error={error} />
  if (!data) return null
  const item = data.items[idx]
  const current = answers[item.id] ?? []
  const answeredCount = Object.keys(answers).length

  const save = async (value: AnswerVal) => {
    setAnswers((a) => ({ ...a, [item.id]: value }))
    if (!value.length || (item.qtype === 'numeric' && String(value[0]).trim() === '')) return
    setSaving(true)
    setErr(null)
    try {
      await api<AnswerOut>('/candidate/testing/answer', { method: 'POST', body: { attempt_id: data.id, item_id: item.id, answer: value } })
    } catch (e) {
      if (e instanceof ApiError && (e.code === 'attempt_expired' || e.code === 'attempt_closed')) {
        nav(`/candidate/results/${data.id}`, { replace: true })
        return
      }
      setErr(errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  const choose = (i: number) => {
    if (item.qtype === 'single') void save([i])
    else void save(current.includes(i) ? current.filter((x) => x !== i) : [...current, i].sort())
  }

  const finish = async () => {
    setFinishing(true)
    try {
      await api<TestResult>('/candidate/testing/finish', { method: 'POST', body: { attempt_id: data.id } })
      nav(`/candidate/results/${data.id}`, { replace: true })
    } catch (e) {
      setErr(errorMessage(e))
      setFinishing(false)
    }
  }

  const mm = String(Math.floor(remaining / 60)).padStart(2, '0')
  const ss = String(remaining % 60).padStart(2, '0')

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>{t('test.run.title', { spec: specName(data.specialization_id), grade: gradeName(data.target_grade) })}</h1>
          <p className="sub">{t('test.run.sub')}</p></div>
        <div className="row">
          <span className={`badge ${remaining < 300 ? 'danger' : 'violet'}`} style={{ fontSize: 15, padding: '8px 14px' }}
            aria-label={t('test.run.timeLeft', { time: `${mm}:${ss}` })}><Clock size={16} />{mm}:{ss}</span>
          <button className="btn" onClick={() => setConfirm(true)}><Flag size={16} />{t('test.run.finish')}</button>
        </div>
      </div>
      <ErrorBox error={err} />

      <div className="split">
        <div className="card" style={{ padding: 26 }}>
          <div className="row between" style={{ marginBottom: 14 }}>
            <span className="badge violet">{t('test.run.question', { n: idx + 1, total: data.total })}</span>
            <span className="badge outline">{item.competency_name}</span>
          </div>
          <RichText text={item.text} />
          <div className="stack" style={{ marginTop: 22 }}>
            {item.qtype === 'numeric' ? (
              <div className="field" style={{ maxWidth: 320 }}>
                <label htmlFor="num">{t('test.run.numeric')}</label>
                <input id="num" className="input" inputMode="decimal" value={current[0] ?? ''} placeholder={t('test.run.numericPlaceholder')}
                  onChange={(e) => setAnswers((a) => ({ ...a, [item.id]: [e.target.value] }))}
                  onBlur={(e) => e.target.value.trim() && save([e.target.value])} />
              </div>
            ) : (
              <>
                {item.qtype === 'multi' && <span className="small muted">{t('test.run.multi')}</span>}
                {item.options.map((o, i) => {
                  const on = current.includes(i)
                  return (
                    <button key={i} className={`option ${item.qtype === 'multi' ? 'multi' : ''} ${on ? 'on' : ''}`} onClick={() => choose(i)} aria-pressed={on}>
                      <span className="mark">{on && <Check size={14} />}</span><span style={{ flex: 1 }}><RichText text={o} /></span>
                    </button>
                  )
                })}
              </>
            )}
          </div>
          <div className="row between" style={{ marginTop: 24 }}>
            <button className="btn ghost" disabled={idx === 0} onClick={() => setIdx(idx - 1)}><ChevronLeft size={16} />{t('test.run.back')}</button>
            <span className="small muted">{saving ? t('test.run.saving') : current.length ? t('test.run.saved') : ''}</span>
            {idx < data.total - 1
              ? <button className="btn" onClick={() => setIdx(idx + 1)}>{t('test.run.next')}<ChevronRight size={16} /></button>
              : <button className="btn success" onClick={() => setConfirm(true)}><Flag size={16} />{t('test.run.finishTest')}</button>}
          </div>
        </div>
        <div className="card sticky stack">
          <div className="row between"><b>{t('test.run.progress')}</b><span className="small muted">{answeredCount} / {data.total}</span></div>
          <div className="bar"><i style={{ width: `${(answeredCount / data.total) * 100}%` }} /></div>
          <div className="qnav" style={{ marginTop: 8 }}>
            {data.items.map((it, i) => (
              <button key={it.id} className={`${answers[it.id]?.length ? 'done' : ''} ${i === idx ? 'cur' : ''}`} onClick={() => setIdx(i)}
                aria-label={t('test.run.question', { n: i + 1, total: data.total })}>{i + 1}</button>
            ))}
          </div>
          <div className="divider" />
          <div className="small muted">{t('test.run.blueprint')}</div>
          {Object.entries(data.blueprint.competency_quota).map(([k, v]) => (
            <div key={k} className="row between tiny"><span>{data.items.find((i) => i.competency_id === k)?.competency_name ?? k}</span><b>{v}</b></div>
          ))}
        </div>
      </div>

      {confirm && (
        <Modal title={t('test.run.confirmTitle')} onClose={() => setConfirm(false)}>
          <p>{t('test.run.answered', { n: answeredCount, total: data.total })} {answeredCount < data.total && t('test.run.unanswered')}</p>
          <div className="row" style={{ marginTop: 18 }}>
            <button className="btn" onClick={finish} disabled={finishing}>{finishing ? t('test.run.counting') : t('test.run.finishAndSee')}</button>
            <button className="btn ghost" onClick={() => setConfirm(false)}>{t('test.run.backToQuestions')}</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
