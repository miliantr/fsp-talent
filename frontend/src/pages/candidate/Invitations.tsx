import { Building2, CheckCircle2, Flag, Inbox, MessageCircle, ShieldCheck, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { Invitation } from '../../api/types'
import { Empty, ErrorBox, InvitationStatusBadge, Loading, Modal, Reasons, useToast } from '../../components/ui'
import type { MessageKey } from '../../i18n/core'
import { useI18n } from '../../i18n/context'
import { workFormatKey } from '../../lib/format'

type Respond = 'accept' | 'reject' | 'report'

export default function CandidateInvitations() {
  const { invId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const { t, fmt, lang } = useI18n()
  const list = useApi<Invitation[]>('/candidate/invitations')
  const [current, setCurrent] = useState<Invitation | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [respond, setRespond] = useState<Respond | null>(null)
  const [message, setMessage] = useState('')

  const selectedId = invId ? Number(invId) : list.data?.[0]?.id

  useEffect(() => {
    if (!selectedId) { setCurrent(null); return }
    // opening the invitation marks it as "viewed" on the server; refetched on a language switch, since the
    // "why you were chosen" reasons are rendered by the server
    api<Invitation>(`/candidate/invitations/${selectedId}`).then((inv) => {
      setCurrent(inv)
      // functional update: the list request may finish before or after this one
      list.setData((prev) => (prev ? prev.map((x) => (x.id === inv.id ? inv : x)) : prev))
    }).catch((e) => setErr(errorMessage(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, lang])

  if (list.loading && !list.data) return <Loading />
  if (list.error) return <ErrorBox error={list.error} onRetry={list.reload} />
  const items = list.data ?? []

  const act = async () => {
    if (!current || !respond) return
    setBusy(true)
    setErr(null)
    try {
      const body = respond === 'report' ? { reason: message || null } : { message: message || null }
      const inv = await api<Invitation>(`/candidate/invitations/${current.id}/${respond}`, { method: 'POST', body })
      setCurrent(inv)
      list.setData(items.map((x) => (x.id === inv.id ? inv : x)))
      toast(t(`cand.inv.done.${respond}` as MessageKey))
      setRespond(null)
      setMessage('')
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  const closedStatus = (s: string) => t(s === 'expired' ? 'cand.inv.closed.expired' : s === 'withdrawn' ? 'cand.inv.closed.withdrawn' : 'cand.inv.closed.rejected')

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>{t('nav.invitations')}</h1>
        <p className="sub">{t('cand.inv.sub')}</p></div></div>
      <ErrorBox error={err} />
      {items.length === 0 ? (
        <div className="card"><Empty icon={<Inbox size={26} />} title={t('cand.inv.emptyTitle')} text={t('cand.inv.emptyText')}
          action={<Link className="btn" to="/candidate">{t('cand.inv.toCabinet')}</Link>} /></div>
      ) : (
        <div className="split-left">
          <div className="stack">
            {items.map((i) => (
              <button key={i.id} onClick={() => nav(`/candidate/invitations/${i.id}`)} className="card hover"
                style={{ textAlign: 'left', cursor: 'pointer', font: 'inherit', borderColor: i.id === selectedId ? 'var(--primary)' : undefined, borderWidth: i.id === selectedId ? 2 : 1, padding: 14 }}>
                <div className="row between"><b className="small">{i.company.name}</b><InvitationStatusBadge status={i.status} /></div>
                <div className="bold" style={{ marginTop: 4 }}>{i.position_title}</div>
                <div className="row between" style={{ marginTop: 6 }}><span className="small" style={{ fontWeight: 700, color: 'var(--primary-700)' }}>{fmt.salaryRange(i.salary_from, i.salary_to)}</span>
                  <span className="tiny muted">{fmt.ago(i.created_at)}</span></div>
              </button>
            ))}
          </div>
          {current && (
            <div className="card" style={{ padding: 26 }}>
              <div className="row between wrap">
                <div className="row"><span className="avatar lg"><Building2 size={26} /></span>
                  <div><div className="small muted">{current.company.industry} · {current.company.city}</div><h2>{current.company.name}</h2></div></div>
                <InvitationStatusBadge status={current.status} />
              </div>
              <div className="divider" />
              <div className="row between wrap" style={{ alignItems: 'flex-end' }}>
                <div><div className="small muted">{t('cand.inv.offer')}</div><h2 style={{ marginTop: 4 }}>{current.position_title}</h2>
                  <div className="small muted" style={{ marginTop: 4 }}>{t(workFormatKey(current.work_format))}
                    {' · '}{current.job_title ? t('cand.inv.forNeed', { title: current.job_title }) : t('cand.inv.noVacancy')}</div></div>
                <div style={{ textAlign: 'right' }}><div className="small muted">{t('cand.inv.salary')}</div>
                  <div className="salary lg">{fmt.salaryRange(current.salary_from, current.salary_to)}</div></div>
              </div>
              <p style={{ marginTop: 18, whiteSpace: 'pre-wrap' }}>{current.description}</p>
              {current.company.description && <p className="small muted" style={{ marginTop: 10 }}>{t('cand.inv.aboutCompany', { text: current.company.description })}</p>}

              {current.match_reasons.length > 0 && (
                <div className="card flat" style={{ marginTop: 18, background: 'var(--surface-2)' }}>
                  <div className="row between"><b>{t('cand.inv.whyYou')}</b>
                    {current.match_score != null && <span className="badge violet">{t('cand.inv.match', { pct: Math.round(current.match_score * 100) })}</span>}</div>
                  <Reasons reasons={current.match_reasons} />
                </div>
              )}

              <div className="card flat" style={{ marginTop: 14 }}>
                <div className="row"><MessageCircle size={18} color="var(--primary)" /><b>{t('cand.inv.contact')}</b></div>
                <p style={{ marginTop: 6 }}>{current.contact_method}</p>
              </div>

              <div className="row wrap" style={{ marginTop: 20 }}>
                {(current.status === 'sent' || current.status === 'viewed') ? (
                  <>
                    <button className="btn success lg" onClick={() => setRespond('accept')}><CheckCircle2 size={18} />{t('cand.inv.accept')}</button>
                    <button className="btn ghost lg" onClick={() => setRespond('reject')}><XCircle size={18} />{t('cand.inv.reject')}</button>
                    <span className="small muted">{t('cand.inv.validUntil', { date: fmt.date(current.expires_at) })}</span>
                    <button className="btn sm ghost right" onClick={() => setRespond('report')}><Flag size={14} />{t('cand.inv.report')}</button>
                  </>
                ) : current.status === 'accepted' ? (
                  <div className="alert success" style={{ width: '100%' }}><ShieldCheck size={18} />
                    <span>{t('cand.inv.accepted', { date: fmt.date(current.responded_at) })}
                      {current.candidate_message ? ` ${t('cand.inv.yourReply', { text: current.candidate_message })}` : ''}</span></div>
                ) : (
                  <div className="alert info" style={{ width: '100%' }}>{t('cand.inv.status')} <b>{closedStatus(current.status)}</b>
                    {current.candidate_message && ` · «${current.candidate_message}»`}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {respond && current && (
        <Modal title={t(`cand.inv.modal.${respond}` as MessageKey)} onClose={() => setRespond(null)}>
          {respond === 'accept' && <div className="alert info" style={{ marginBottom: 14 }}><ShieldCheck size={18} />{t('cand.inv.acceptNotice', { company: current.company.name })}</div>}
          {respond === 'report' && <p className="small muted" style={{ marginBottom: 10 }}>{t('cand.inv.reportHint')}</p>}
          <div className="field"><label htmlFor="invitations-f1">{respond === 'report' ? t('cand.inv.reason') : t('cand.inv.message')}</label>
            <textarea id="invitations-f1" className="textarea" value={message} onChange={(e) => setMessage(e.target.value)} /></div>
          <div className="row" style={{ marginTop: 16 }}>
            <button className={`btn ${respond === 'accept' ? 'success' : respond === 'reject' ? '' : 'danger'}`} onClick={act} disabled={busy}>{busy ? '…' : t('cand.inv.confirm')}</button>
            <button className="btn ghost" onClick={() => setRespond(null)}>{t('common.cancel')}</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
