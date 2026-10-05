import { FileText } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { EmployerApplication } from '../../api/types'
import { ApplicationStatusBadge, CategoryBadge, Empty, ErrorBox, FspSummary, Loading, useToast } from '../../components/ui'
import { ago } from '../../lib/format'

export default function EmployerApplications() {
  const { data, error, loading, reload } = useApi<EmployerApplication[]>('/employer/applications')
  const toast = useToast()
  const [err, setErr] = useState<string | null>(null)
  const setStatus = async (id: number, status: string) => {
    try {
      await api(`/employer/applications/${id}/status`, { method: 'POST', body: { status } })
      toast('Статус обновлён')
      await reload()
    } catch (e) {
      setErr(errorMessage(e))
    }
  }
  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>Отклики на вакансии</h1><p className="sub">Кандидаты, откликнувшиеся сами, раскрывают вам контакты сразу.</p></div></div>
      <ErrorBox error={err} />
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} /> : (data ?? []).length === 0 ? (
        <div className="card"><Empty icon={<FileText size={26} />} title="Откликов пока нет" text="Опубликуйте потребность как вакансию, чтобы кандидаты могли откликаться." /></div>
      ) : (
        <div className="stack">
          {data!.map((a) => (
            <div key={a.id} className="card">
              <div className="row between wrap">
                <div className="stack" style={{ gap: 6 }}>
                  <div className="row wrap"><Link to={`/employer/candidates/${a.candidate.candidate_id}?requirement_id=${a.job.id}`} className="bold">{a.contacts.full_name}</Link>
                    <CategoryBadge category={a.candidate.category} /><FspSummary fsp={a.candidate.fsp} compact /></div>
                  <div className="small muted">на «{a.job.title}» · {ago(a.created_at)}{a.match_percent != null ? ` · совпадение ${a.match_percent}%` : ''}</div>
                  <div className="small">✉ {a.contacts.email}{a.contacts.phone ? ` · ${a.contacts.phone}` : ''}{a.contacts.telegram ? ` · ${a.contacts.telegram}` : ''}</div>
                  {a.cover_letter && <p className="small" style={{ marginTop: 4 }}>«{a.cover_letter}»</p>}
                </div>
                <div className="stack" style={{ alignItems: 'flex-end' }}>
                  <ApplicationStatusBadge status={a.status} />
                  <div className="row">
                    <button className="btn sm success" onClick={() => setStatus(a.id, 'accepted')}>Пригласить</button>
                    <button className="btn sm ghost" onClick={() => setStatus(a.id, 'rejected')}>Отказать</button>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
