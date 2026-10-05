import { Inbox, Undo2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { Invitation } from '../../api/types'
import { Empty, ErrorBox, InvitationStatusBadge, Loading, useToast } from '../../components/ui'
import { ago, INVITATION_STATUS, salaryRange } from '../../lib/format'

export default function EmployerInvitations() {
  const [status, setStatus] = useState('')
  const { data, error, loading, reload } = useApi<Invitation[]>('/employer/invitations', { status })
  const toast = useToast()
  const [err, setErr] = useState<string | null>(null)

  const withdraw = async (id: number) => {
    try {
      await api(`/employer/invitations/${id}/withdraw`, { method: 'POST' })
      toast('Приглашение отозвано')
      await reload()
    } catch (e) {
      setErr(errorMessage(e))
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>Приглашения</h1><p className="sub">История приглашений и актуальные статусы. Контакты кандидата появляются после принятия приглашения.</p></div>
        <select className="select" style={{ width: 220 }} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Все статусы</option>{Object.entries(INVITATION_STATUS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}</select></div>
      <ErrorBox error={err} />
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} /> : (data ?? []).length === 0 ? (
        <div className="card"><Empty icon={<Inbox size={26} />} title="Приглашений нет" text="Пригласите кандидатов из подборки по потребности." action={<Link className="btn" to="/employer/requirements">К подборкам</Link>} /></div>
      ) : (
        <div className="card table-wrap"><table className="table">
          <thead><tr><th>Кандидат</th><th>Предложение</th><th>Зарплата</th><th>Совпадение</th><th>Статус</th><th>Контакты</th><th /></tr></thead>
          <tbody>{data!.map((i) => (
            <tr key={i.id}>
              <td><Link to={`/employer/candidates/${i.candidate.id}${i.job_id ? `?requirement_id=${i.job_id}` : ''}`} className="bold">{i.candidate.display_name}</Link>
                <div className="tiny muted">{i.candidate.category_label}</div></td>
              <td>{i.position_title}<div className="tiny muted">{ago(i.created_at)}{i.viewed_at ? ' · просмотрено' : ''}</div></td>
              <td className="small">{salaryRange(i.salary_from, i.salary_to)}</td>
              <td>{i.match_score != null ? `${Math.round(i.match_score * 100)}%` : '—'}</td>
              <td><InvitationStatusBadge status={i.status} />{i.candidate_message && <div className="tiny muted" style={{ maxWidth: 200 }}>«{i.candidate_message}»</div>}</td>
              <td className="small">{i.contacts ? <>{i.contacts.full_name}<div className="tiny">{i.contacts.email}</div><div className="tiny">{i.contacts.phone} {i.contacts.telegram}</div></> : <span className="muted tiny">скрыты</span>}</td>
              <td>{(i.status === 'sent' || i.status === 'viewed') && <button className="btn sm ghost" onClick={() => withdraw(i.id)}><Undo2 size={14} />Отозвать</button>}</td>
            </tr>
          ))}</tbody></table></div>
      )}
    </div>
  )
}
