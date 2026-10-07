import { ListChecks } from 'lucide-react'
import { useState } from 'react'
import { api, errorMessage } from '../api/client'
import { useApi } from '../api/hooks'
import type { EmployerTask, TasksSignal } from '../api/types'
import { useI18n } from '../i18n/context'
import { useToast } from './ui'

/** Recent regular-task results of a candidate: a fresh signal for the employer. */
export function TasksSignalBadge({ signal }: { signal: TasksSignal | null | undefined }) {
  const { t, fmt } = useI18n()
  if (!signal) return null
  const title = t('signal.tasksTitle', { title: signal.last_title, when: fmt.ago(signal.last_at) })
  if (signal.done === 0) return <span className="badge muted" title={title}><ListChecks size={12} />{t('signal.tasksPending')}</span>
  return (
    <span className={`badge ${(signal.avg_score ?? 0) >= 60 ? 'success' : 'warning'}`} title={title}>
      <ListChecks size={12} />{t('signal.tasks', { done: signal.done, score: signal.avg_score ?? 0 })}
    </span>
  )
}

/** The employer offers one of its active tasks to this candidate personally. */
export function OfferTaskCard({ candidateId, specialization }: { candidateId: number; specialization?: string | null }) {
  const { t } = useI18n()
  const toast = useToast()
  const { data } = useApi<EmployerTask[]>('/employer/tasks')
  const active = (data ?? []).filter((x) => x.is_active && (!specialization || x.specialization_id === specialization))
  const [taskId, setTaskId] = useState('')
  const [err, setErr] = useState<string | null>(null)
  const offer = async () => {
    setErr(null)
    try {
      await api(`/employer/tasks/${taskId || active[0].id}/offer`, { method: 'POST', body: { candidate_id: candidateId } })
      toast(t('emp.tasks.offered'))
    } catch (e) {
      setErr(errorMessage(e))
    }
  }
  return (
    <div className="card stack">
      <h3><ListChecks size={18} color="var(--primary)" />{t('emp.tasks.offer')}</h3>
      {active.length === 0 ? <p className="small muted" style={{ margin: 0 }}>{t('emp.tasks.noActive')}</p> : (
        <>
          <select className="select" aria-label={t('emp.tasks.offer')} value={taskId} onChange={(e) => setTaskId(e.target.value)}>
            {active.map((x) => <option key={x.id} value={x.id}>{x.title}</option>)}
          </select>
          <p className="tiny muted" style={{ margin: 0 }}>{t('emp.tasks.offerHint')}</p>
          {err && <div className="alert danger small">{err}</div>}
          <button className="btn secondary sm" onClick={offer}>{t('emp.tasks.offer')}</button>
        </>
      )}
    </div>
  )
}
