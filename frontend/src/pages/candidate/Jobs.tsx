import { Briefcase, Search, Send } from 'lucide-react'
import { useState } from 'react'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { ApplicationOut, PublicJob } from '../../api/types'
import { ApplicationStatusBadge, Empty, ErrorBox, Loading, Modal, ScoreRing, Tabs, useToast } from '../../components/ui'
import { ago, salaryRange, WORK_FORMAT } from '../../lib/format'
import { useReference } from '../../lib/reference'

export default function CandidateJobs() {
  const [tab, setTab] = useState<'jobs' | 'mine'>('jobs')
  const [q, setQ] = useState('')
  const [spec, setSpec] = useState('')
  const { ref } = useReference()
  const jobs = useApi<PublicJob[]>(tab === 'jobs' ? '/jobs' : null, { q, specialization_id: spec })
  const mine = useApi<ApplicationOut[]>(tab === 'mine' ? '/applications' : null)
  const toast = useToast()
  const [applyTo, setApplyTo] = useState<PublicJob | null>(null)
  const [letter, setLetter] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const apply = async () => {
    if (!applyTo) return
    setBusy(true)
    setErr(null)
    try {
      await api<ApplicationOut>('/applications', { method: 'POST', body: { job_id: applyTo.id, cover_letter: letter } })
      toast('Отклик отправлен — работодатель увидит ваши контакты')
      setApplyTo(null)
      setLetter('')
      await jobs.reload()
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="stack-lg">
      <div className="page-head">
        <div><h1>Вакансии и отклики</h1><p className="sub">Дополнительный сценарий: пока приглашений нет, можно проявить инициативу. Вакансии отсортированы по совпадению с вашим подтверждённым профилем.</p></div>
        <Tabs value={tab} onChange={setTab} items={[{ id: 'jobs', label: 'Вакансии' }, { id: 'mine', label: 'Мои отклики' }]} />
      </div>
      {tab === 'jobs' && (
        <>
          <div className="row wrap">
            <div style={{ position: 'relative', flex: 1, minWidth: 220 }}>
              <Search size={16} style={{ position: 'absolute', left: 12, top: 13, color: 'var(--muted)' }} />
              <input className="input" style={{ paddingLeft: 36 }} placeholder="Должность, компания, технология" value={q} onChange={(e) => setQ(e.target.value)} />
            </div>
            <select className="select" style={{ width: 200 }} value={spec} onChange={(e) => setSpec(e.target.value)}>
              <option value="">Все специализации</option>{ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select>
          </div>
          {jobs.loading && !jobs.data ? <Loading /> : jobs.error ? <ErrorBox error={jobs.error} /> : (jobs.data ?? []).length === 0 ? (
            <div className="card"><Empty icon={<Briefcase size={26} />} title="Вакансий не найдено" text="Попробуйте изменить запрос или фильтр." /></div>
          ) : (
            <div className="stack">
              {jobs.data!.map((j) => (
                <div key={j.id} className="cand" style={{ gridTemplateColumns: 'auto 1fr auto' }}>
                  {j.match_percent != null ? <ScoreRing value={j.match_percent} size={64} /> : <span className="avatar"><Briefcase size={20} /></span>}
                  <div className="stack" style={{ gap: 6 }}>
                    <div className="row wrap"><span className="name">{j.title}</span><span className="badge violet">{j.specialization_name} · {j.grade_name}</span></div>
                    <div className="small muted">{j.company.name} · {WORK_FORMAT[j.work_format]}{j.city ? ` · ${j.city}` : ''} · {ago(j.created_at)}</div>
                    <p className="small">{j.description}</p>
                    <div className="row wrap">{j.skills.map((s) => <span key={s.slug} className="chip">{s.name}{s.importance === 'nice' && <span className="tiny muted">·жел.</span>}</span>)}</div>
                  </div>
                  <div className="actions">
                    <div className="salary" style={{ fontSize: 18, textAlign: 'right' }}>{salaryRange(j.salary_from, j.salary_to)}</div>
                    {j.application_status ? <ApplicationStatusBadge status={j.application_status} />
                      : <button className="btn sm" onClick={() => setApplyTo(j)}><Send size={14} />Откликнуться</button>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
      {tab === 'mine' && (mine.loading && !mine.data ? <Loading /> : mine.error ? <ErrorBox error={mine.error} /> : (mine.data ?? []).length === 0 ? (
        <div className="card"><Empty title="Откликов пока нет" text="Откликнитесь на вакансию — статус будет виден здесь." /></div>
      ) : (
        <div className="card table-wrap"><table className="table">
          <thead><tr><th>Вакансия</th><th>Компания</th><th>Зарплата</th><th>Совпадение</th><th>Статус</th><th>Дата</th></tr></thead>
          <tbody>{mine.data!.map((a) => (
            <tr key={a.id}><td className="bold">{a.job.title}</td><td>{a.job.company.name}</td><td>{salaryRange(a.job.salary_from, a.job.salary_to)}</td>
              <td>{a.match_percent != null ? `${a.match_percent}%` : '—'}</td><td><ApplicationStatusBadge status={a.status} /></td><td className="small muted">{ago(a.created_at)}</td></tr>
          ))}</tbody></table></div>
      ))}

      {applyTo && (
        <Modal title={`Отклик: ${applyTo.title}`} onClose={() => setApplyTo(null)}>
          <p className="small muted">{applyTo.company.name} · {salaryRange(applyTo.salary_from, applyTo.salary_to)}</p>
          <div className="alert info small" style={{ margin: '12px 0' }}>Откликаясь, вы раскрываете работодателю свои контакты.</div>
          <div className="field"><label htmlFor="jobs-f1">Сопроводительное письмо</label><textarea id="jobs-f1" className="textarea" value={letter} onChange={(e) => setLetter(e.target.value)} placeholder="Почему вам интересна эта вакансия" /></div>
          <ErrorBox error={err} />
          <div className="row" style={{ marginTop: 14 }}><button className="btn" onClick={apply} disabled={busy}>{busy ? 'Отправляем…' : 'Отправить отклик'}</button>
            <button className="btn ghost" onClick={() => setApplyTo(null)}>Отмена</button></div>
        </Modal>
      )}
    </div>
  )
}
