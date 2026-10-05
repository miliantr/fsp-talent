import { Send, ShieldCheck } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { api, errorMessage } from '../api/client'
import type { Invitation, Requirement } from '../api/types'
import { useI18n } from '../i18n/context'
import { WORK_FORMATS, workFormatKey } from '../lib/format'
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
  const { t } = useI18n()
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const from = Number(form.salary_from)
    const to = Number(form.salary_to)
    if (!from || !to) return setErr(t('invite.salaryRequired'))
    if (to < from) return setErr(t('invite.salaryInverted'))
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
    <Modal title={t('invite.title', { name: candidateName })} onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <div className="alert violet small"><ShieldCheck size={16} />{t('invite.notice')}</div>
        <div className="field"><label htmlFor="invitemodal-f1">{t('invite.position')}</label><input id="invitemodal-f1" className="input" required minLength={3} value={form.position_title} onChange={set('position_title')} /></div>
        <div className="field"><label htmlFor="invitemodal-f2">{t('invite.description')}</label><textarea id="invitemodal-f2" className="textarea" required minLength={10} value={form.description} onChange={set('description')}
          placeholder={t('invite.descriptionPlaceholder')} /></div>
        <div className="grid grid-3">
          <div className="field"><label htmlFor="invitemodal-f3">{t('invite.salaryFrom')}</label><input id="invitemodal-f3" className="input" type="number" required min={1} step="any" value={form.salary_from} onChange={set('salary_from')} /></div>
          <div className="field"><label htmlFor="invitemodal-f4">{t('invite.salaryTo')}</label><input id="invitemodal-f4" className="input" type="number" required min={1} step="any" value={form.salary_to} onChange={set('salary_to')} /></div>
          <div className="field"><label htmlFor="invitemodal-f5">{t('invite.format')}</label><select id="invitemodal-f5" className="select" value={form.work_format} onChange={set('work_format')}>
            {WORK_FORMATS.map((k) => <option key={k} value={k}>{t(workFormatKey(k))}</option>)}</select></div>
        </div>
        <div className="field"><label htmlFor="invitemodal-f6">{t('invite.contact')}</label><input id="invitemodal-f6" className="input" required minLength={3} value={form.contact_method} onChange={set('contact_method')} placeholder={t('invite.contactPlaceholder')} /></div>
        <p className="tiny muted">{requirement ? t('invite.linked', { title: requirement.title }) : t('invite.unlinked')}</p>
        <ErrorBox error={err} />
        <div className="row"><button className="btn" disabled={busy}><Send size={16} />{busy ? t('common.sending') : t('invite.send')}</button>
          <button type="button" className="btn ghost" onClick={onClose}>{t('common.cancel')}</button></div>
      </form>
    </Modal>
  )
}
