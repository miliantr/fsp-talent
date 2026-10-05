import { ListChecks, Star } from 'lucide-react'
import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { TaskOut } from '../../api/types'
import { Empty, ErrorBox, Loading, Modal, useToast } from '../../components/ui'
import { ago } from '../../lib/format'

export default function CandidateTasks() {
  const { data, error, loading, reload } = useApi<TaskOut[]>('/candidate/tasks')
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
      toast('Решение отправлено — профиль отмечен как активный')
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
      <div className="page-head"><div><h1>Короткие задания</h1>
        <p className="sub">Работодатели периодически публикуют небольшие задачи. Решение или предложенный подход — свежий сигнал о вас: профиль поднимается в подборках как актуальный.</p></div></div>
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} /> : (data ?? []).length === 0 ? (
        <div className="card"><Empty icon={<ListChecks size={26} />} title="Заданий по вашей специализации пока нет" /></div>
      ) : (
        <div className="grid grid-2">
          {data!.map((t) => (
            <div key={t.id} className="card stack">
              <div className="row between"><span className="badge violet">{t.specialization_name}</span><span className="tiny muted">{t.company.name} · {ago(t.created_at)}</span></div>
              <h3>{t.title}</h3>
              <p className="small">{t.description}</p>
              <div className="row between" style={{ marginTop: 'auto' }}>
                <span className="tiny muted">Решений: {t.submissions}</span>
                {t.my_submission ? (
                  <span className="badge success">{t.my_submission.rating ? <><Star size={12} />Оценка {t.my_submission.rating}/5</> : 'Отправлено, ждёт оценки'}</span>
                ) : <button className="btn sm" onClick={() => setOpen(t)}>Предложить решение</button>}
              </div>
              {t.my_submission?.reviewer_comment && <div className="alert info small">Комментарий: {t.my_submission.reviewer_comment}</div>}
            </div>
          ))}
        </div>
      )}
      {open && (
        <Modal title={open.title} onClose={() => setOpen(null)}>
          <p className="small">{open.description}</p>
          <div className="field" style={{ marginTop: 14 }}><label htmlFor="tasks-f1">Решение или подход</label>
            <textarea id="tasks-f1" className="textarea" style={{ minHeight: 180 }} value={answer} onChange={(e) => setAnswer(e.target.value)} /></div>
          <ErrorBox error={err} />
          <div className="row" style={{ marginTop: 14 }}><button className="btn" disabled={busy || answer.trim().length < 20} onClick={submit}>Отправить</button>
            <button className="btn ghost" onClick={() => setOpen(null)}>Отмена</button></div>
        </Modal>
      )}
    </div>
  )
}
