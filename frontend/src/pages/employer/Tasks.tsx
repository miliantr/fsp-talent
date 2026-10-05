import { ListChecks, Plus, Star } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { SubmissionOut, TaskOut } from '../../api/types'
import { Empty, ErrorBox, Loading, Modal, useToast } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { useReference } from '../../lib/reference'

function Submissions({ task, onClose }: { task: TaskOut; onClose: () => void }) {
  const { data, loading, reload } = useApi<SubmissionOut[]>(`/employer/tasks/${task.id}/submissions`)
  const { t, fmt } = useI18n()
  const toast = useToast()
  const rate = async (id: number, rating: number) => {
    await api(`/employer/submissions/${id}/review`, { method: 'POST', body: { rating } })
    toast(t('emp.tasks.rated'))
    await reload()
  }
  return (
    <Modal title={t('emp.tasks.solutionsTitle', { title: task.title })} onClose={onClose} wide>
      {loading && !data ? <Loading /> : (data ?? []).length === 0 ? <p className="muted">{t('emp.tasks.noSolutions')}</p> : (
        <div className="stack">{data!.map((s) => (
          <div key={s.id} className="card flat">
            <div className="row between"><b>{s.candidate_name}</b><span className="tiny muted">{fmt.ago(s.created_at)}</span></div>
            <p className="small" style={{ marginTop: 6, whiteSpace: 'pre-wrap' }}>{s.answer}</p>
            <div className="row" style={{ marginTop: 8 }}>{[1, 2, 3, 4, 5].map((n) => (
              <button key={n} className="icon-btn" onClick={() => rate(s.id, n)} aria-label={t('emp.tasks.rate', { n })}>
                <Star size={18} fill={s.rating && n <= s.rating ? 'var(--gold)' : 'none'} color="var(--gold)" /></button>))}</div>
          </div>
        ))}</div>
      )}
    </Modal>
  )
}

export default function EmployerTasks() {
  const { data, error, loading, reload } = useApi<TaskOut[]>('/employer/tasks')
  const { ref } = useReference()
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [creating, setCreating] = useState(false)
  const [open, setOpen] = useState<TaskOut | null>(null)
  const [form, setForm] = useState({ specialization_id: 'backend', title: '', description: '' })
  const [err, setErr] = useState<string | null>(null)

  const create = async (e: FormEvent) => {
    e.preventDefault()
    setErr(null)
    try {
      await api('/employer/tasks', { method: 'POST', body: form })
      toast(t('emp.tasks.published'))
      setCreating(false)
      setForm({ specialization_id: 'backend', title: '', description: '' })
      await reload()
    } catch (ex) {
      setErr(errorMessage(ex))
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.tasks')}</h1><p className="sub">{t('emp.tasks.sub')}</p></div>
        <button className="btn" onClick={() => setCreating(true)}><Plus size={16} />{t('emp.tasks.new')}</button></div>
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} /> : (data ?? []).length === 0 ? (
        <div className="card"><Empty icon={<ListChecks size={26} />} title={t('emp.tasks.empty')} /></div>
      ) : (
        <div className="grid grid-2">{data!.map((task) => (
          <div key={task.id} className="card stack">
            <div className="row between"><span className="badge violet">{task.specialization_name}</span><span className="tiny muted">{fmt.ago(task.created_at)}</span></div>
            <h3>{task.title}</h3><p className="small">{task.description}</p>
            <div className="row between"><span className="small">{t('cand.tasks.solutions', { n: task.submissions })}</span>
              <button className="btn sm secondary" onClick={() => setOpen(task)}>{t('emp.tasks.view')}</button></div>
          </div>
        ))}</div>
      )}
      {open && <Submissions task={open} onClose={() => { setOpen(null); void reload() }} />}
      {creating && (
        <Modal title={t('emp.tasks.newTitle')} onClose={() => setCreating(false)}>
          <form className="stack" onSubmit={create}>
            <div className="field"><label htmlFor="tasks-f1">{t('cand.profile.spec')}</label><select id="tasks-f1" className="select" value={form.specialization_id} onChange={(e) => setForm({ ...form, specialization_id: e.target.value })}>
              {ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
            <div className="field"><label htmlFor="tasks-f2">{t('emp.tasks.title')}</label><input id="tasks-f2" className="input" required minLength={3} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></div>
            <div className="field"><label htmlFor="tasks-f3">{t('emp.tasks.statement')}</label><textarea id="tasks-f3" className="textarea" required minLength={10} value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></div>
            <ErrorBox error={err} />
            <div className="row"><button className="btn">{t('emp.tasks.publish')}</button><button type="button" className="btn ghost" onClick={() => setCreating(false)}>{t('common.cancel')}</button></div>
          </form>
        </Modal>
      )}
    </div>
  )
}
