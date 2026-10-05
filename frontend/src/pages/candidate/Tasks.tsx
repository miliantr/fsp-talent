import { ListChecks, Star } from 'lucide-react'
import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { TaskOut } from '../../api/types'
import { Empty, ErrorBox, Loading, Modal, useToast } from '../../components/ui'
import { useI18n } from '../../i18n/context'

export default function CandidateTasks() {
  const { data, error, loading, reload } = useApi<TaskOut[]>('/candidate/tasks')
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [open, setOpen] = useState<TaskOut | null>(null)
  const [answer, setAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const submit = async () => {
    if (!open) return
    setBusy(true)
    setErr(null)
    try {
      await api(`/candidate/tasks/${open.id}/submit`, { method: 'POST', body: { answer } })
      toast(t('cand.tasks.sent'))
      setOpen(null)
      setAnswer('')
      await reload()
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.tasks')}</h1><p className="sub">{t('cand.tasks.sub')}</p></div></div>
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} /> : (data ?? []).length === 0 ? (
        <div className="card"><Empty icon={<ListChecks size={26} />} title={t('cand.tasks.empty')} /></div>
      ) : (
        <div className="grid grid-2">
          {data!.map((task) => (
            <div key={task.id} className="card stack">
              <div className="row between"><span className="badge violet">{task.specialization_name}</span>
                <span className="tiny muted">{task.company.name} · {fmt.ago(task.created_at)}</span></div>
              <h3>{task.title}</h3>
              <p className="small">{task.description}</p>
              <div className="row between" style={{ marginTop: 'auto' }}>
                <span className="tiny muted">{t('cand.tasks.solutions', { n: task.submissions })}</span>
                {task.my_submission ? (
                  <span className="badge success">{task.my_submission.rating
                    ? <><Star size={12} />{t('cand.tasks.rating', { n: task.my_submission.rating })}</> : t('cand.tasks.awaiting')}</span>
                ) : <button className="btn sm" onClick={() => setOpen(task)}>{t('cand.tasks.propose')}</button>}
              </div>
              {task.my_submission?.reviewer_comment && <div className="alert info small">{t('cand.tasks.comment', { text: task.my_submission.reviewer_comment })}</div>}
            </div>
          ))}
        </div>
      )}
      {open && (
        <Modal title={open.title} onClose={() => setOpen(null)}>
          <p className="small">{open.description}</p>
          <div className="field" style={{ marginTop: 14 }}><label htmlFor="tasks-f1">{t('cand.tasks.answer')}</label>
            <textarea id="tasks-f1" className="textarea" style={{ minHeight: 180 }} value={answer} onChange={(e) => setAnswer(e.target.value)} /></div>
          <ErrorBox error={err} />
          <div className="row" style={{ marginTop: 14 }}><button className="btn" disabled={busy || answer.trim().length < 20} onClick={submit}>{t('cand.tasks.send')}</button>
            <button className="btn ghost" onClick={() => setOpen(null)}>{t('common.cancel')}</button></div>
        </Modal>
      )}
    </div>
  )
}
