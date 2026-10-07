import { CheckCircle2, EyeOff, ListChecks, Plus, XCircle } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { EmployerTask, Requirement, SubmissionOut } from '../../api/types'
import { Empty, ErrorBox, Loading, Modal, Tabs, useToast } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'
import { useReference } from '../../lib/reference'
import { TaskBadges } from '../candidate/Tasks'

const RUBRIC = ['correctness', 'completeness', 'reasoning'] as const
type Rubric = Record<(typeof RUBRIC)[number], number>

function Review({ s, onSaved }: { s: SubmissionOut; onSaved: () => void }) {
  const { t } = useI18n()
  const toast = useToast()
  const [rubric, setRubric] = useState<Rubric>({ correctness: s.rubric?.correctness ?? 1, completeness: s.rubric?.completeness ?? 1, reasoning: s.rubric?.reasoning ?? 1 })
  const [comment, setComment] = useState(s.reviewer_comment ?? '')
  const [err, setErr] = useState<string | null>(null)
  const save = async () => {
    setErr(null)
    try {
      await api(`/employer/submissions/${s.id}/review`, { method: 'POST', body: { rubric, comment: comment || null } })
      toast(t('emp.tasks.rated'))
      onSaved()
    } catch (e) {
      setErr(errorMessage(e))
    }
  }
  return (
    <div className="stack" style={{ gap: 8 }}>
      {RUBRIC.map((k) => (
        <div key={k} className="row between wrap" style={{ gap: 8 }}>
          <span className="small" title={t(`tasks.rubric.${k}.hint`)}><b>{t(`tasks.rubric.${k}`)}</b> <span className="muted">· {t(`tasks.rubric.${k}.hint`)}</span></span>
          <div className="row" role="group" aria-label={t(`tasks.rubric.${k}`)} style={{ gap: 4 }}>
            {[0, 1, 2].map((v) => (
              <button key={v} type="button" className={`chip ${rubric[k] === v ? 'on' : ''}`} aria-pressed={rubric[k] === v}
                onClick={() => setRubric({ ...rubric, [k]: v })}>{v}</button>
            ))}
          </div>
        </div>
      ))}
      <textarea className="textarea" style={{ minHeight: 60 }} placeholder={t('cand.tasks.comment', { text: '' })} value={comment} onChange={(e) => setComment(e.target.value)} />
      <ErrorBox error={err} />
      <div className="row"><button className="btn sm" onClick={save}>{t('emp.tasks.saveReview')}</button></div>
    </div>
  )
}

function Submissions({ task, onClose }: { task: EmployerTask; onClose: () => void }) {
  const { data, loading, reload } = useApi<SubmissionOut[]>(`/employer/tasks/${task.id}/submissions`)
  const { t, fmt } = useI18n()
  return (
    <Modal title={t('emp.tasks.solutionsTitle', { title: task.title })} onClose={onClose} wide>
      {loading && !data ? <Loading /> : (data ?? []).length === 0 ? <p className="muted">{t('emp.tasks.noSolutions')}</p> : (
        <div className="stack">{data!.map((s) => {
          const matched = (s.auto_detail?.matched ?? []) as string[]
          const missed = (s.auto_detail?.missed ?? []) as string[]
          return (
            <div key={s.id} className="card flat stack" style={{ gap: 10 }}>
              <div className="row between wrap"><div><b>{s.candidate_name}</b>{s.category_label && <span className="tiny muted"> · {s.category_label}</span>}</div>
                <span className="tiny muted">{fmt.ago(s.created_at)}</span></div>
              <p className="small" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{s.answer}</p>
              {task.mode === 'solve' ? (
                s.auto_score === 1 ? <span className="badge success" style={{ width: 'fit-content' }}><CheckCircle2 size={12} />{t('emp.tasks.autoCorrect')}</span>
                  : <span className="badge danger" style={{ width: 'fit-content' }}><XCircle size={12} />{t('emp.tasks.autoWrong')}</span>
              ) : (
                <>
                  <div className="row wrap" style={{ gap: 6 }}>
                    {s.auto_score != null && <span className="badge info" title={t('emp.tasks.preScoreHint')}>{t('emp.tasks.preScore', { score: Math.round(s.auto_score * 100) })}</span>}
                    {s.score != null && <span className={`badge ${s.score >= 60 ? 'success' : 'warning'}`}>{t('emp.tasks.final', { score: s.score })}</span>}
                  </div>
                  {(matched.length > 0 || missed.length > 0) && (
                    <ul className="small" style={{ margin: 0, paddingLeft: 0, listStyle: 'none' }}>
                      {matched.map((p) => <li key={p}><CheckCircle2 size={13} color="var(--success)" /> {p}</li>)}
                      {missed.map((p) => <li key={p} className="muted"><XCircle size={13} color="var(--danger)" /> {p}</li>)}
                    </ul>
                  )}
                  <Review s={s} onSaved={reload} />
                </>
              )}
            </div>
          )
        })}</div>
      )}
    </Modal>
  )
}

const EMPTY = {
  specialization_id: 'backend', title: '', description: '', mode: 'approach' as 'approach' | 'solve',
  audience: 'targeted' as 'targeted' | 'category', grade_id: '', job_id: '', competency_id: '',
  answer_kind: 'number' as 'number' | 'text', value: '', tolerance: '0', accepted: '', key_points: '',
  time_limit_days: 7, max_offers: 20,
}

export default function EmployerTasks() {
  const { data, error, loading, reload } = useApi<EmployerTask[]>('/employer/tasks')
  const reqs = useApi<Requirement[]>('/employer/requirements')
  const { ref } = useReference()
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [creating, setCreating] = useState(false)
  const [open, setOpen] = useState<EmployerTask | null>(null)
  const [form, setForm] = useState(EMPTY)
  const [err, setErr] = useState<string | null>(null)
  const set = <K extends keyof typeof EMPTY>(k: K, v: (typeof EMPTY)[K]) => setForm((f) => ({ ...f, [k]: v }))
  const spec = ref?.specializations.find((s) => s.id === form.specialization_id)

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setErr(null)
    const body = {
      specialization_id: form.specialization_id, title: form.title, description: form.description, mode: form.mode,
      audience: form.audience, grade_id: form.grade_id || null, job_id: form.job_id ? Number(form.job_id) : null,
      competency_id: form.competency_id || null, time_limit_days: form.time_limit_days, max_offers: form.max_offers,
      key_points: form.mode === 'approach' ? form.key_points.split('\n').map((s) => s.trim()).filter(Boolean) : [],
      answer_spec: form.mode === 'solve' ? (form.answer_kind === 'number'
        ? { kind: 'number', value: Number(form.value.replace(',', '.')), tolerance: Number(form.tolerance.replace(',', '.')) || 0 }
        : { kind: 'text', accepted: form.accepted.split(',').map((s) => s.trim()).filter(Boolean) }) : null,
    }
    try {
      await api('/employer/tasks', { method: 'POST', body })
      toast(t('emp.tasks.published'))
      setCreating(false)
      setForm(EMPTY)
      await reload()
    } catch (ex) {
      setErr(errorMessage(ex))
    }
  }

  const toggle = async (task: EmployerTask) => {
    await api(`/employer/tasks/${task.id}/active`, { method: 'PUT', body: { is_active: !task.is_active } })
    await reload()
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.tasks')}</h1><p className="sub">{t('emp.tasks.sub')}</p></div>
        <button className="btn" onClick={() => setCreating(true)}><Plus size={16} />{t('emp.tasks.new')}</button></div>
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} /> : (data ?? []).length === 0 ? (
        <div className="card"><Empty icon={<ListChecks size={26} />} title={t('emp.tasks.empty')} /></div>
      ) : (
        <div className="grid grid-2">{data!.map((task) => (
          <div key={task.id} className="card stack" style={{ opacity: task.is_active ? 1 : 0.65 }}>
            <div className="row between wrap"><TaskBadges task={task} /><span className="tiny muted">{fmt.ago(task.created_at)}</span></div>
            <div><h3>{task.title}{!task.is_active && <span className="badge muted" style={{ marginLeft: 8 }}><EyeOff size={12} />{t('emp.tasks.inactive')}</span>}</h3>
              {task.requirement_title && <div className="small muted">{t('tasks.requirement', { title: task.requirement_title })}</div>}</div>
            <p className="small" style={{ margin: 0 }}>{task.description}</p>
            <div className="small">{t('emp.tasks.stats', { offered: task.stats.offered, submitted: task.stats.submitted, pending: task.stats.pending_review })}
              {task.stats.avg_score != null && <> · <b>{t('emp.tasks.avg', { score: task.stats.avg_score })}</b></>}</div>
            <div className="row" style={{ marginTop: 'auto' }}>
              <button className="btn sm secondary" onClick={() => setOpen(task)}>{t('emp.tasks.view')}</button>
              <button className="btn sm ghost" onClick={() => toggle(task)}>{task.is_active ? t('emp.tasks.deactivate') : t('emp.tasks.activate')}</button>
            </div>
          </div>
        ))}</div>
      )}
      {open && <Submissions task={open} onClose={() => { setOpen(null); void reload() }} />}
      {creating && (
        <Modal title={t('emp.tasks.newTitle')} onClose={() => setCreating(false)} wide>
          <form className="stack" onSubmit={create}>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="tasks-spec">{t('cand.profile.spec')}</label>
                <select id="tasks-spec" className="select" value={form.specialization_id} onChange={(e) => setForm({ ...form, specialization_id: e.target.value, competency_id: '', job_id: '' })}>
                  {ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
              <div className="field"><label htmlFor="tasks-grade">{t('emp.tasks.grade')}</label>
                <select id="tasks-grade" className="select" value={form.grade_id} onChange={(e) => set('grade_id', e.target.value)}>
                  <option value="">{t('emp.tasks.anyGrade')}</option>{ref?.grades.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
            </div>
            <div className="field"><label htmlFor="tasks-title">{t('emp.tasks.title')}</label><input id="tasks-title" className="input" required minLength={3} value={form.title} onChange={(e) => set('title', e.target.value)} /></div>
            <div className="field"><label htmlFor="tasks-statement">{t('emp.tasks.statement')}</label><textarea id="tasks-statement" className="textarea" required minLength={10} value={form.description} onChange={(e) => set('description', e.target.value)} /></div>
            <div className="field"><span className="label">{t('emp.tasks.mode')}</span>
              <Tabs value={form.mode} onChange={(v) => set('mode', v)} items={[{ id: 'approach', label: t('tasks.mode.approach') }, { id: 'solve', label: t('tasks.mode.solve') }]} />
              <span className="tiny muted">{t(`tasks.mode.${form.mode}.hint` as MessageKey)}</span></div>
            {form.mode === 'solve' ? (
              <div className="grid grid-3">
                <div className="field"><label htmlFor="tasks-kind">{t('emp.tasks.answerKind')}</label>
                  <select id="tasks-kind" className="select" value={form.answer_kind} onChange={(e) => set('answer_kind', e.target.value as 'number' | 'text')}>
                    <option value="number">{t('emp.tasks.kind.number')}</option><option value="text">{t('emp.tasks.kind.text')}</option></select></div>
                {form.answer_kind === 'number' ? (<>
                  <div className="field"><label htmlFor="tasks-value">{t('emp.tasks.correctValue')}</label><input id="tasks-value" className="input" inputMode="decimal" required value={form.value} onChange={(e) => set('value', e.target.value)} /></div>
                  <div className="field"><label htmlFor="tasks-tol">{t('emp.tasks.tolerance')}</label><input id="tasks-tol" className="input" inputMode="decimal" value={form.tolerance} onChange={(e) => set('tolerance', e.target.value)} /></div>
                </>) : (
                  <div className="field" style={{ gridColumn: 'span 2' }}><label htmlFor="tasks-accepted">{t('emp.tasks.accepted')}</label><input id="tasks-accepted" className="input" required value={form.accepted} onChange={(e) => set('accepted', e.target.value)} /></div>
                )}
              </div>
            ) : (
              <div className="field"><label htmlFor="tasks-points">{t('emp.tasks.keyPoints')}</label>
                <textarea id="tasks-points" className="textarea" value={form.key_points} onChange={(e) => set('key_points', e.target.value)} />
                <span className="tiny muted">{t('emp.tasks.keyPointsHint')}</span></div>
            )}
            <div className="field"><span className="label">{t('emp.tasks.audience')}</span>
              <Tabs value={form.audience} onChange={(v) => set('audience', v)} items={[{ id: 'targeted', label: t('tasks.audience.targeted') }, { id: 'category', label: t('tasks.audience.category') }]} />
              <span className="tiny muted">{t(`emp.tasks.audience.${form.audience}.hint` as MessageKey)}</span></div>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="tasks-req">{t('emp.tasks.requirement')}</label>
                <select id="tasks-req" className="select" value={form.job_id} onChange={(e) => set('job_id', e.target.value)}>
                  <option value="">{t('emp.tasks.noRequirement')}</option>
                  {(reqs.data ?? []).filter((r) => r.specialization_id === form.specialization_id && r.status === 'active').map((r) => <option key={r.id} value={r.id}>{r.title}</option>)}</select>
                <span className="tiny muted">{t('emp.tasks.requirementHint')}</span></div>
              <div className="field"><label htmlFor="tasks-comp">{t('emp.tasks.competency')}</label>
                <select id="tasks-comp" className="select" value={form.competency_id} onChange={(e) => set('competency_id', e.target.value)}>
                  <option value="">{t('emp.tasks.anyCompetency')}</option>{spec?.competencies.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            </div>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="tasks-limit">{t('emp.tasks.timeLimit')}</label><input id="tasks-limit" type="number" min={1} max={30} className="input" value={form.time_limit_days} onChange={(e) => set('time_limit_days', Number(e.target.value))} /></div>
              <div className="field"><label htmlFor="tasks-max">{t('emp.tasks.maxOffers')}</label><input id="tasks-max" type="number" min={1} max={200} className="input" value={form.max_offers} onChange={(e) => set('max_offers', Number(e.target.value))} /></div>
            </div>
            <ErrorBox error={err} />
            <div className="row"><button className="btn">{t('emp.tasks.publish')}</button><button type="button" className="btn ghost" onClick={() => setCreating(false)}>{t('common.cancel')}</button></div>
          </form>
        </Modal>
      )}
    </div>
  )
}
