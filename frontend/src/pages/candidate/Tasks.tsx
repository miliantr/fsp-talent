import { CheckCircle2, Clock, Info, ListChecks, Send, Sparkles, UserCheck, XCircle } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { CandidateTasks, TaskResult, TaskView } from '../../api/types'
import { Empty, ErrorBox, Loading, Modal, useToast } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'

/** Format, audience, grade and competency of a task as badges. */
export function TaskBadges({ task, personal }: { task: TaskView; personal?: boolean }) {
  const { t } = useI18n()
  return (
    <div className="row wrap" style={{ gap: 6 }}>
      <span className={`badge ${task.mode === 'solve' ? 'info' : 'violet'}`}>{t(`tasks.mode.${task.mode}` as MessageKey)}</span>
      {personal ? <span className="badge accent"><UserCheck size={12} />{t('cand.tasks.fromEmployer')}</span>
        : <span className="badge outline">{t(`tasks.audience.${task.audience}` as MessageKey)}</span>}
      <span className="badge muted">{task.specialization_name}{task.grade_name ? ` · ${t('tasks.forGrade', { grade: task.grade_name })}` : ''}</span>
      {task.competency_name && <span className="badge outline">{t('tasks.competency', { name: task.competency_name })}</span>}
    </div>
  )
}

function ResultBadge({ r }: { r: TaskResult }) {
  const { t } = useI18n()
  if (r.mode === 'solve') {
    return r.correct ? <span className="badge success"><CheckCircle2 size={12} />{t('cand.tasks.correct')}</span>
      : <span className="badge danger"><XCircle size={12} />{t('cand.tasks.wrong')}</span>
  }
  if (r.score == null) return <span className="badge warning"><Clock size={12} />{t('cand.tasks.awaiting')}</span>
  return <span className={`badge ${r.score >= 60 ? 'success' : 'warning'}`}>{t('cand.tasks.score', { score: r.score })}</span>
}

const RUBRIC = ['correctness', 'completeness', 'reasoning'] as const

export default function CandidateTasks() {
  const { data, error, loading, reload } = useApi<CandidateTasks>('/candidate/tasks')
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [open, setOpen] = useState<TaskView | null>(null)
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async () => {
    if (!open) return
    setBusy(true)
    setErr(null)
    try {
      const r = await api<TaskResult>(`/candidate/tasks/${open.id}/submit`, { method: 'POST', body: { answer } })
      toast(r.mode === 'solve' ? `${t('cand.tasks.sentChecked')}: ${r.correct ? t('cand.tasks.correct') : t('cand.tasks.wrong')}`
        : t('cand.tasks.sentReview'))
      setOpen(null)
      setAnswer('')
      await reload()
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const decline = async (assignmentId: number) => {
    try {
      await api(`/candidate/tasks/offers/${assignmentId}/decline`, { method: 'POST' })
      toast(t('cand.tasks.declined'))
      await reload()
    } catch (e) {
      toast(errorMessage(e))
    }
  }

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data) return null
  const valid = open?.mode === 'approach' ? answer.trim().length >= 20 : answer.trim().length > 0

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.tasks')}</h1><p className="sub">{t('cand.tasks.sub')}</p></div></div>
      {!data.verified && (
        <div className="alert violet"><Info size={18} /><span>{t('cand.tasks.notVerified')} <Link to="/candidate/testing">{t('nav.testing')}</Link></span></div>
      )}

      <div className="card stack">
        <div className="card-title" style={{ marginBottom: 0 }}><h3><Sparkles size={18} color="var(--primary)" />{t('cand.tasks.offered')}</h3>
          <span className="tiny muted">{t('cand.tasks.cadence', { n: data.interval_days })}</span></div>
        {data.offered.length === 0 ? (
          <p className="small muted" style={{ margin: 0 }}>{t('cand.tasks.offeredEmpty')}
            {data.next_offer_at ? ` ${t('cand.tasks.nextOffer', { date: fmt.date(data.next_offer_at) })}` : ''}</p>
        ) : data.offered.map((o) => (
          <div key={o.assignment_id} className="card flat stack" style={{ borderColor: 'var(--primary)' }}>
            <div className="row between wrap"><TaskBadges task={o.task} personal={o.source === 'employer'} />
              <span className="tiny muted"><Clock size={12} /> {t('cand.tasks.due', { date: fmt.date(o.due_at) })}</span></div>
            <div><h3>{o.task.title}</h3><div className="small muted">{o.task.company.name}
              {o.task.requirement_title ? ` · ${t('tasks.requirement', { title: o.task.requirement_title })}` : ''}</div></div>
            <p className="small" style={{ margin: 0 }}>{o.task.description}</p>
            <div className="small"><b>{t('cand.tasks.why')}</b>
              <ul style={{ margin: '4px 0 0', paddingLeft: 18 }}>{o.reasons.map((r) => <li key={r}>{r}</li>)}</ul></div>
            <div className="row"><button className="btn sm" onClick={() => { setOpen(o.task); setAnswer(''); setErr(null) }}>{t('cand.tasks.solve')}</button>
              <button className="btn ghost sm" onClick={() => decline(o.assignment_id)}>{t('cand.tasks.decline')}</button></div>
          </div>
        ))}
      </div>

      <div className="card stack">
        <div className="card-title" style={{ marginBottom: 0 }}><h3>{t('cand.tasks.challenges')}</h3>
          <span className="tiny muted">{t('cand.tasks.challengesHint')}</span></div>
        {data.challenges.length === 0 ? <p className="small muted" style={{ margin: 0 }}>{t('cand.tasks.challengesEmpty')}</p> : (
          <div className="grid grid-2">{data.challenges.map((task) => (
            <div key={task.id} className="card flat stack">
              <TaskBadges task={task} />
              <div><h3>{task.title}</h3><div className="small muted">{task.company.name} · {fmt.ago(task.created_at)}</div></div>
              <p className="small" style={{ margin: 0 }}>{task.description}</p>
              <div className="row" style={{ marginTop: 'auto' }}><button className="btn sm secondary" onClick={() => { setOpen(task); setAnswer(''); setErr(null) }}>{t('cand.tasks.solve')}</button></div>
            </div>
          ))}</div>
        )}
      </div>

      <div className="card stack">
        <div className="card-title" style={{ marginBottom: 0 }}><h3><ListChecks size={18} color="var(--primary)" />{t('cand.tasks.history')}</h3></div>
        {data.history.length === 0 ? <Empty icon={<ListChecks size={26} />} title={t('cand.tasks.historyEmpty')} /> : data.history.map((r) => (
          <div key={r.id} className="card flat stack" style={{ gap: 8 }}>
            <div className="row between wrap"><div><b>{r.task_title}</b><div className="tiny muted">{r.company.name} · {fmt.ago(r.created_at)}</div></div>
              <ResultBadge r={r} /></div>
            <p className="small" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{r.answer}</p>
            {r.rubric && (
              <div className="row wrap" style={{ gap: 6 }}>{RUBRIC.map((k) => (
                <span key={k} className="badge outline" title={t(`tasks.rubric.${k}.hint`)}>{t(`tasks.rubric.${k}`)}: {r.rubric?.[k] ?? 0}/2</span>
              ))}</div>
            )}
            {r.reviewer_comment && <div className="alert info small">{t('cand.tasks.comment', { text: r.reviewer_comment })}</div>}
          </div>
        ))}
      </div>

      {open && (
        <Modal title={open.title} onClose={() => setOpen(null)}>
          <TaskBadges task={open} />
          <p className="small" style={{ marginTop: 12 }}>{open.description}</p>
          <div className="alert info small"><Info size={16} /><span>{t(`tasks.mode.${open.mode}.hint` as MessageKey)}</span></div>
          <div className="field" style={{ marginTop: 14 }}>
            <label htmlFor="tasks-answer">{open.mode === 'approach' ? t('cand.tasks.answerApproach')
              : open.answer_kind === 'number' ? t('cand.tasks.answerNumber') : t('cand.tasks.answerText')}</label>
            {open.mode === 'approach'
              ? <textarea id="tasks-answer" className="textarea" style={{ minHeight: 180 }} value={answer} onChange={(e) => setAnswer(e.target.value)} />
              : <input id="tasks-answer" className="input" inputMode={open.answer_kind === 'number' ? 'decimal' : 'text'} value={answer} onChange={(e) => setAnswer(e.target.value)} />}
          </div>
          <ErrorBox error={err} />
          <div className="row" style={{ marginTop: 14 }}><button className="btn" disabled={busy || !valid} onClick={submit}><Send size={15} />{t('cand.tasks.send')}</button>
            <button className="btn ghost" onClick={() => setOpen(null)}>{t('common.cancel')}</button></div>
        </Modal>
      )}
    </div>
  )
}
