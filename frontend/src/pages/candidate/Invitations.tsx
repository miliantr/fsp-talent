import { Building2, CheckCircle2, Flag, Inbox, MessageCircle, ShieldCheck, XCircle } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { Invitation } from '../../api/types'
import { Empty, ErrorBox, InvitationStatusBadge, Loading, Modal, Reasons, useToast } from '../../components/ui'
import { ago, date, salaryRange, WORK_FORMAT } from '../../lib/format'

export default function CandidateInvitations() {
  const { invId } = useParams()
  const nav = useNavigate()
  const toast = useToast()
  const list = useApi<Invitation[]>('/candidate/invitations')
  const [current, setCurrent] = useState<Invitation | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [respond, setRespond] = useState<'accept' | 'reject' | 'report' | null>(null)
  const [message, setMessage] = useState('')

  const selectedId = invId ? Number(invId) : list.data?.[0]?.id

  useEffect(() => {
    if (!selectedId) { setCurrent(null); return }
    // opening the invitation marks it as "viewed" on the server
    api<Invitation>(`/candidate/invitations/${selectedId}`).then((inv) => {
      setCurrent(inv)
      list.setData((list.data ?? []).map((x) => (x.id === inv.id ? inv : x)))
    }).catch((e) => setErr(errorMessage(e)))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId])

  if (list.loading && !list.data) return <Loading />
  if (list.error) return <ErrorBox error={list.error} onRetry={list.reload} />
  const items = list.data ?? []

  const act = async () => {
    if (!current || !respond) return
    setBusy(true)
    setErr(null)
    try {
      const path = respond === 'report' ? 'report' : respond
      const body = respond === 'report' ? { reason: message || null } : { message: message || null }
      const inv = await api<Invitation>(`/candidate/invitations/${current.id}/${path}`, { method: 'POST', body })
      setCurrent(inv)
      list.setData(items.map((x) => (x.id === inv.id ? inv : x)))
      toast(respond === 'accept' ? 'Приглашение принято — работодатель получил ваши контакты' : respond === 'reject' ? 'Приглашение отклонено' : 'Жалоба отправлена')
      setRespond(null)
      setMessage('')
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>Приглашения</h1>
        <p className="sub">Работодатели сами выходят на вас с конкретным предложением и зарплатой. Условия видны до начала общения, контакты — только после вашего согласия.</p></div></div>
      <ErrorBox error={err} />
      {items.length === 0 ? (
        <div className="card"><Empty icon={<Inbox size={26} />} title="Приглашений пока нет"
          text="Подтвердите категорию, включите публикацию профиля и привяжите ФСП ID — так вас быстрее найдут."
          action={<Link className="btn" to="/candidate">В кабинет</Link>} /></div>
      ) : (
        <div className="split-left">
          <div className="stack">
            {items.map((i) => (
              <button key={i.id} onClick={() => nav(`/candidate/invitations/${i.id}`)} className="card hover"
                style={{ textAlign: 'left', cursor: 'pointer', font: 'inherit', borderColor: i.id === selectedId ? 'var(--primary)' : undefined, borderWidth: i.id === selectedId ? 2 : 1, padding: 14 }}>
                <div className="row between"><b className="small">{i.company.name}</b><InvitationStatusBadge status={i.status} /></div>
                <div className="bold" style={{ marginTop: 4 }}>{i.position_title}</div>
                <div className="row between" style={{ marginTop: 6 }}><span className="small" style={{ fontWeight: 700, color: 'var(--primary-700)' }}>{salaryRange(i.salary_from, i.salary_to)}</span>
                  <span className="tiny muted">{ago(i.created_at)}</span></div>
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
                <div><div className="small muted">Предложение</div><h2 style={{ marginTop: 4 }}>{current.position_title}</h2>
                  <div className="small muted" style={{ marginTop: 4 }}>{WORK_FORMAT[current.work_format]}{current.job_title ? ` · по потребности «${current.job_title}»` : ' · без привязки к вакансии'}</div></div>
                <div style={{ textAlign: 'right' }}><div className="small muted">Зарплата, ₽ в месяц</div><div className="salary lg">{salaryRange(current.salary_from, current.salary_to)}</div></div>
              </div>
              <p style={{ marginTop: 18, whiteSpace: 'pre-wrap' }}>{current.description}</p>
              {current.company.description && <p className="small muted" style={{ marginTop: 10 }}>О компании: {current.company.description}</p>}

              {current.match_reasons.length > 0 && (
                <div className="card flat" style={{ marginTop: 18, background: 'var(--surface-2)' }}>
                  <div className="row between"><b>Почему выбрали вас</b>{current.match_score != null && <span className="badge violet">совпадение {Math.round(current.match_score * 100)}%</span>}</div>
                  <Reasons reasons={current.match_reasons} />
                </div>
              )}

              <div className="card flat" style={{ marginTop: 14 }}>
                <div className="row"><MessageCircle size={18} color="var(--primary)" /><b>Способ связи с работодателем</b></div>
                <p style={{ marginTop: 6 }}>{current.contact_method}</p>
              </div>

              <div className="row wrap" style={{ marginTop: 20 }}>
                {(current.status === 'sent' || current.status === 'viewed') ? (
                  <>
                    <button className="btn success lg" onClick={() => setRespond('accept')}><CheckCircle2 size={18} />Принять</button>
                    <button className="btn ghost lg" onClick={() => setRespond('reject')}><XCircle size={18} />Отклонить</button>
                    <span className="small muted">Действует до {date(current.expires_at)}</span>
                    <button className="btn sm ghost right" onClick={() => setRespond('report')}><Flag size={14} />Пожаловаться</button>
                  </>
                ) : current.status === 'accepted' ? (
                  <div className="alert success" style={{ width: '100%' }}><ShieldCheck size={18} />
                    <span>Вы приняли приглашение {date(current.responded_at)} — работодатель получил ваши контакты и свяжется с вами.{current.candidate_message ? ` Ваш ответ: «${current.candidate_message}»` : ''}</span></div>
                ) : (
                  <div className="alert info" style={{ width: '100%' }}>Статус: <b>{current.status === 'expired' ? 'срок приглашения истёк' : current.status === 'withdrawn' ? 'работодатель отозвал приглашение' : 'вы отклонили приглашение'}</b>
                    {current.candidate_message && ` · «${current.candidate_message}»`}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {respond && current && (
        <Modal title={respond === 'accept' ? 'Принять приглашение' : respond === 'reject' ? 'Отклонить приглашение' : 'Пожаловаться'} onClose={() => setRespond(null)}>
          {respond === 'accept' && <div className="alert info" style={{ marginBottom: 14 }}><ShieldCheck size={18} />Компания «{current.company.name}» увидит ваши ФИО, e-mail, телефон и Telegram.</div>}
          {respond === 'report' && <p className="small muted" style={{ marginBottom: 10 }}>Например: фиктивная вакансия, зарплата не соответствует, спам. Приглашение будет отклонено, а жалоба учтена при модерации работодателя.</p>}
          <div className="field"><label htmlFor="invitations-f1">{respond === 'report' ? 'Причина' : 'Сообщение работодателю (необязательно)'}</label>
            <textarea id="invitations-f1" className="textarea" value={message} onChange={(e) => setMessage(e.target.value)} /></div>
          <div className="row" style={{ marginTop: 16 }}>
            <button className={`btn ${respond === 'accept' ? 'success' : respond === 'reject' ? '' : 'danger'}`} onClick={act} disabled={busy}>{busy ? '…' : 'Подтвердить'}</button>
            <button className="btn ghost" onClick={() => setRespond(null)}>Отмена</button>
          </div>
        </Modal>
      )}
    </div>
  )
}
