import { Send, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../api/client'
import type { Invitation, Requirement } from '../api/types'
import { WORK_FORMAT } from '../lib/format'
import { ErrorBox, Modal } from './ui'

export function InviteModal({ candidateId, candidateName, requirement, defaultContact, onClose, onSent }: {
  candidateId: number
  candidateName: string
  requirement?: Requirement | null
  defaultContact?: string
  onClose: () => void
  onSent: (inv: Invitation) => void
}) {
  const [form, setForm] = useState({
    position_title: requirement?.title ?? '',
    description: requirement ? [requirement.description, requirement.team_description].filter(Boolean).join('\n\n') : '',
    salary_from: requirement ? String(requirement.salary_from) : '',
    salary_to: requirement ? String(requirement.salary_to) : '',
    work_format: requirement?.work_format ?? 'any',
    contact_method: defaultContact ?? '',
  })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const from = Number(form.salary_from)
    const to = Number(form.salary_to)
    if (!from || !to) return setErr('Укажите зарплатную вилку — это обязательное условие приглашения')
    if (to < from) return setErr('Верхняя граница вилки меньше нижней')
    setBusy(true)
    setErr(null)
    try {
      const inv = await api<Invitation>('/employer/invitations', {
        method: 'POST',
        body: { candidate_id: candidateId, job_id: requirement?.id ?? null, ...form, salary_from: from, salary_to: to },
      })
      onSent(inv)
    } catch (ex) {
      setErr(errorMessage(ex))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={`Пригласить: ${candidateName}`} onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <div className="alert violet small"><ShieldCheck size={16} />Кандидат увидит компанию, предложение и зарплату до ответа. Его контакты откроются вам после принятия приглашения.</div>
        <div className="field"><label htmlFor="invitemodal-f1">Должность / предложение</label><input id="invitemodal-f1" className="input" required minLength={3} value={form.position_title} onChange={set('position_title')} /></div>
        <div className="field"><label htmlFor="invitemodal-f2">Описание предложения</label><textarea id="invitemodal-f2" className="textarea" required minLength={10} value={form.description} onChange={set('description')}
          placeholder="Задачи, команда, чем интересно предложение" /></div>
        <div className="grid grid-3">
          <div className="field"><label htmlFor="invitemodal-f3">Зарплата от, ₽</label><input id="invitemodal-f3" className="input" type="number" required min={1} step="any" value={form.salary_from} onChange={set('salary_from')} /></div>
          <div className="field"><label htmlFor="invitemodal-f4">до, ₽</label><input id="invitemodal-f4" className="input" type="number" required min={1} step="any" value={form.salary_to} onChange={set('salary_to')} /></div>
          <div className="field"><label htmlFor="invitemodal-f5">Формат</label><select id="invitemodal-f5" className="select" value={form.work_format} onChange={set('work_format')}>
            {Object.entries(WORK_FORMAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
        </div>
        <div className="field"><label htmlFor="invitemodal-f6">Способ связи</label><input id="invitemodal-f6" className="input" required minLength={3} value={form.contact_method} onChange={set('contact_method')} placeholder="Telegram @hr, телефон или e-mail рекрутера" /></div>
        {requirement ? <p className="tiny muted">Приглашение привязано к потребности «{requirement.title}» — кандидат увидит, почему его выбрали.</p>
          : <p className="tiny muted">Приглашение без привязки к вакансии.</p>}
        <ErrorBox error={err} />
        <div className="row"><button className="btn" disabled={busy}><Send size={16} />{busy ? 'Отправляем…' : 'Отправить приглашение'}</button>
          <button type="button" className="btn ghost" onClick={onClose}>Отмена</button></div>
      </form>
    </Modal>
  )
}
