import { ChevronRight, Search, Send } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { BankOut, CandidateCard, Company } from '../../api/types'
import { InviteModal } from '../../components/InviteModal'
import { SkillSelect } from '../../components/SkillPicker'
import { Avatar, CategoryBadge, Empty, ErrorBox, FspSummary, InvitationStatusBadge, Loading, ScoreRing, useToast } from '../../components/ui'
import { rub, WORK_FORMAT, years } from '../../lib/format'
import { useReference } from '../../lib/reference'

export default function Bank() {
  const { ref } = useReference()
  const toast = useToast()
  const [spec, setSpec] = useState('')
  const [grades, setGrades] = useState<string[]>([])
  const [skills, setSkills] = useState<string[]>([])
  const [hasFsp, setHasFsp] = useState('')
  const { data, error, loading, reload } = useApi<BankOut>('/employer/candidates', {
    specialization_id: spec, grades, skills, has_fsp: hasFsp || undefined,
  })
  const company = useApi<Company>('/employer/profile')
  const [invite, setInvite] = useState<CandidateCard | null>(null)

  return (
    <div className="stack-lg">
      <div className="page-head"><div><h1>Банк кандидатов</h1>
        <p className="sub">Вся база подтверждённых кандидатов. Внутри категории — по силе подтверждённого профиля: результат теста, достижения ФСП, актуальность.
          Для ранжирования под конкретную задачу <Link to="/employer/requirements/new">опишите потребность</Link>.</p></div></div>
      <div className="card">
        <div className="grid grid-4" style={{ alignItems: 'end' }}>
          <div className="field"><label htmlFor="bank-f1">Специализация</label><select id="bank-f1" className="select" value={spec} onChange={(e) => setSpec(e.target.value)}>
            <option value="">Все</option>{ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
          <div className="field"><label>Грейд</label><div className="row wrap">
            {ref?.grades.map((g) => <button key={g.id} className={`chip selectable ${grades.includes(g.id) ? 'on' : ''}`}
              onClick={() => setGrades(grades.includes(g.id) ? grades.filter((x) => x !== g.id) : [...grades, g.id])}>{g.name}</button>)}</div></div>
          <div className="field"><label htmlFor="bank-f2">Достижения ФСП</label><select id="bank-f2" className="select" value={hasFsp} onChange={(e) => setHasFsp(e.target.value)}>
            <option value="">Не важно</option><option value="true">Есть</option><option value="false">Нет</option></select></div>
          <div className="field"><label>Стек</label><SkillSelect value={skills} onChange={setSkills} specialization={spec} placeholder="Добавить навык" /></div>
        </div>
      </div>
      {data && <div className="row wrap">{data.categories.map((c) => <span key={c.label} className="chip">{c.label} · {c.count}</span>)}</div>}
      {loading && !data ? <Loading /> : error ? <ErrorBox error={error} onRetry={reload} /> : !data || data.items.length === 0 ? (
        <div className="card"><Empty icon={<Search size={26} />} title="Никого не нашли" text="Ослабьте фильтры: например, уберите грейд или часть навыков." /></div>
      ) : (
        <div className="stack">
          <span className="small muted">Найдено: {data.total}</span>
          {data.items.map((c) => (
            <div key={c.candidate_id} className="cand">
              <div className="stack" style={{ alignItems: 'center', gap: 4 }}><ScoreRing value={c.profile_strength ?? 0} size={70} label="сила" /></div>
              <div className="stack" style={{ gap: 8 }}>
                <div className="row"><Avatar name={c.display_name} /><div><div className="name">{c.display_name}</div>
                  <div className="small muted">{c.headline} · {years(c.experience_years)} · {c.city ?? '—'} · {WORK_FORMAT[c.work_format]}{c.expected_salary ? ` · ${rub(c.expected_salary)}` : ''}</div></div></div>
                <div className="row wrap"><CategoryBadge category={c.category} /><span className="badge outline">Тест {c.category?.scaled_score}/100</span><FspSummary fsp={c.fsp} compact /></div>
                <div className="row wrap">{c.skills.map((s) => <span key={s.slug} className={`chip ${s.verified ? 'verified' : ''}`}>{s.name}</span>)}</div>
              </div>
              <div className="actions">
                {c.invitation_status && <InvitationStatusBadge status={c.invitation_status} />}
                <Link className="btn secondary sm" to={`/employer/candidates/${c.candidate_id}`}>Профиль<ChevronRight size={14} /></Link>
                <button className="btn sm" onClick={() => setInvite(c)}><Send size={14} />Пригласить</button>
              </div>
            </div>
          ))}
        </div>
      )}
      {invite && (
        <InviteModal candidateId={invite.candidate_id} candidateName={invite.display_name}
          defaultContact={[company.data?.contact_telegram, company.data?.contact_email].filter(Boolean).join(' · ')}
          onClose={() => setInvite(null)} onSent={() => { setInvite(null); toast('Приглашение отправлено'); void reload() }} />
      )}
    </div>
  )
}
