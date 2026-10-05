import { Lock, Mail, Phone, Send, ShieldCheck, Trophy, Unlock } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useApi } from '../../api/hooks'
import type { CandidateDetail, Company, Requirement } from '../../api/types'
import { InviteModal } from '../../components/InviteModal'
import {
  AchievementList,
  Avatar,
  CategoryBadge,
  CompetencyBars,
  Empty,
  ErrorBox,
  FspSummary,
  InvitationStatusBadge,
  Loading,
  MatchBreakdown,
  OutcomeBadge,
  Reasons,
  ScoreRing,
  ScoreScale,
  SkillMatchChips,
  useToast,
} from '../../components/ui'
import { ago, date, rub, salaryRange, WORK_FORMAT, years } from '../../lib/format'
import { useReference } from '../../lib/reference'

export default function CandidateView() {
  const { candidateId } = useParams()
  const [params] = useSearchParams()
  const reqId = params.get('requirement_id')
  const toast = useToast()
  const { gradeName, specName } = useReference()
  const { data: c, error, loading, reload } = useApi<CandidateDetail>(`/employer/candidates/${candidateId}`, { requirement_id: reqId })
  const req = useApi<Requirement>(reqId ? `/employer/requirements/${reqId}` : null)
  const company = useApi<Company>('/employer/profile')
  const [invite, setInvite] = useState(false)

  if (loading && !c) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!c) return null
  const active = c.invitations.find((i) => i.status === 'sent' || i.status === 'viewed')

  return (
    <div className="stack-lg">
      {reqId && <Link to={`/employer/requirements/${reqId}`} className="small">← К подборке{req.data ? ` «${req.data.title}»` : ''}</Link>}
      <div className="card" style={{ padding: 24 }}>
        <div className="row between wrap" style={{ alignItems: 'flex-start', gap: 20 }}>
          <div className="row" style={{ alignItems: 'flex-start', gap: 16 }}>
            <Avatar name={c.display_name} size="lg" />
            <div className="stack" style={{ gap: 8 }}>
              <h1>{c.display_name}</h1>
              <div className="muted">{c.headline} · {years(c.experience_years)} опыта · {c.city ?? '—'} · {WORK_FORMAT[c.work_format]}</div>
              <div className="row wrap"><CategoryBadge category={c.category} size="lg" /><FspSummary fsp={c.fsp} /></div>
            </div>
          </div>
          <div className="row" style={{ gap: 20 }}>
            {c.match && <div className="center"><ScoreRing value={c.match.percent} size={104} /><div className="tiny muted" style={{ marginTop: 4 }}>совпадение с потребностью</div></div>}
            <div className="stack">
              <button className="btn lg" disabled={!!active} onClick={() => setInvite(true)}><Send size={18} />{active ? 'Приглашение отправлено' : 'Пригласить'}</button>
              {c.expected_salary && <span className="small muted center">Ожидания: {rub(c.expected_salary)}</span>}
            </div>
          </div>
        </div>
      </div>

      <div className="split">
        <div className="stack-lg">
          {c.match ? (
            <div className="card stack-lg">
              <div className="card-title" style={{ marginBottom: 0 }}><h3>Почему этот кандидат в подборке</h3>{req.data && <span className="small muted">для «{req.data.title}»</span>}</div>
              <Reasons reasons={c.match.reasons} />
              <div><div className="label" style={{ marginBottom: 8 }}>Стек: обязательные и желательные навыки</div><SkillMatchChips items={c.match.skill_matches} />
                <p className="tiny muted" style={{ marginTop: 8 }}>Зелёный — подтверждён тестом · жёлтый — близкий навык засчитан частично · красный — отсутствует</p></div>
              <div><div className="label" style={{ marginBottom: 8 }}>Вклад факторов в {c.match.percent}%</div>
                <MatchBreakdown components={c.match.components} mustGate={c.match.must_gate} detailed /></div>
            </div>
          ) : (
            <div className="alert info">Откройте профиль из подборки, чтобы увидеть совпадение с конкретной потребностью.</div>
          )}

          <div className="card">
            <div className="card-title"><h3>Подтверждённый уровень</h3>{c.category && <span className="small muted">тест от {date(c.category.verified_at)}</span>}</div>
            {c.category?.scaled_score != null && <ScoreScale score={c.category.scaled_score} />}
            <div className="grid grid-2" style={{ marginTop: 18 }}>
              <div><div className="label" style={{ marginBottom: 8 }}>Компетенции</div><CompetencyBars items={c.competencies} /></div>
              <div><div className="label" style={{ marginBottom: 8 }}>История тестирования</div>
                {c.test_history.map((h) => (
                  <div key={h.attempt_id} className="row between small" style={{ padding: '6px 0', borderBottom: '1px solid var(--border)' }}>
                    <span>{specName(h.specialization_id)} · {gradeName(h.target_grade)}</span><span className="row"><b>{h.scaled_score}</b><OutcomeBadge outcome={h.outcome} /></span></div>
                ))}</div>
            </div>
          </div>

          <div className="card">
            <div className="card-title"><h3><Trophy size={18} color="var(--accent)" />Достижения ФСП</h3></div>
            {c.fsp_profile?.achievements.length ? <AchievementList items={c.fsp_profile.achievements} />
              : <Empty icon={<Trophy size={24} />} title="Истории ФСП нет" text="Это не снижает рейтинг кандидата: сигнал ФСП просто не используется." />}
          </div>

          <div className="card">
            <h3>О кандидате</h3>
            <p style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{c.about || '—'}</p>
            <div className="row wrap" style={{ marginTop: 12 }}>
              {c.skills.map((s) => <span key={s.slug} className={`chip ${s.verified ? 'verified' : ''}`}>{s.verified && <ShieldCheck size={12} />}{s.name} · {s.level}/5</span>)}</div>
            {(c.team_roles.length > 0 || c.soft_skills.length > 0) && (
              <div className="row wrap" style={{ marginTop: 12 }}>
                {c.team_roles.map((r) => <span key={r} className="badge violet">{r}</span>)}
                {c.soft_skills.map((r) => <span key={r} className="badge outline">{r}</span>)}</div>
            )}
            {c.education && <p className="small muted" style={{ marginTop: 10 }}>Образование: {c.education}</p>}
          </div>
        </div>

        <div className="stack-lg sticky">
          <div className="card stack">
            <h3 className="row">{c.contacts_visible ? <Unlock size={18} color="var(--success)" /> : <Lock size={18} />}Контакты</h3>
            {c.contacts ? (
              <>
                <div className="alert success small">{c.contacts_reason === 'invitation_accepted' ? 'Кандидат принял ваше приглашение' : 'Кандидат откликнулся на вашу вакансию'}</div>
                <div className="bold">{c.contacts.full_name}</div>
                <div className="row small"><Mail size={14} /><a href={`mailto:${c.contacts.email}`}>{c.contacts.email}</a></div>
                {c.contacts.phone && <div className="row small"><Phone size={14} />{c.contacts.phone}</div>}
                {c.contacts.telegram && <div className="row small">✈ {c.contacts.telegram}</div>}
              </>
            ) : (
              <p className="small muted">Скрыты до тех пор, пока кандидат не примет ваше приглашение или не откликнется сам. Так кандидат видит ваши условия до начала общения.</p>
            )}
          </div>
          <div className="card stack">
            <h3>Ваши приглашения</h3>
            {c.invitations.length === 0 ? <p className="small muted">Ещё не приглашали.</p> : c.invitations.map((i) => (
              <div key={i.id} className="stack" style={{ gap: 4, paddingBottom: 8, borderBottom: '1px solid var(--border)' }}>
                <div className="row between"><b className="small">{i.position_title}</b><InvitationStatusBadge status={i.status} /></div>
                <span className="tiny muted">{salaryRange(i.salary_from, i.salary_to)} · {ago(i.created_at)}</span>
                {i.candidate_message && <span className="tiny">«{i.candidate_message}»</span>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {invite && (
        <InviteModal candidateId={c.candidate_id} candidateName={c.display_name} requirement={req.data}
          defaultContact={[company.data?.contact_telegram, company.data?.contact_email].filter(Boolean).join(' · ')}
          onClose={() => setInvite(false)} onSent={() => { setInvite(false); toast('Приглашение отправлено'); void reload() }} />
      )}
    </div>
  )
}
