import { ArrowLeftRight, ChevronRight, Pencil, RefreshCcw, Send, SlidersHorizontal, Star, Users } from 'lucide-react'
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { CandidateCard, CompareOut, Company, MatchList } from '../../api/types'
import { InviteModal } from '../../components/InviteModal'
import {
  Avatar,
  CategoryBadge,
  Empty,
  ErrorBox,
  FspSummary,
  InvitationStatusBadge,
  Loading,
  MatchBreakdown,
  Modal,
  Reasons,
  ScoreRing,
  SkillMatchChips,
  useToast,
} from '../../components/ui'
import { activeAgo, ago, COMPONENT_COLORS, experienceFrom, rub, salaryRange, WORK_FORMAT, years } from '../../lib/format'

interface Filters { grades: string[]; categories: string[]; has_fsp: '' | 'true' | 'false'; min_score: number; skills: string[]; shortlisted: boolean }
const NO_FILTERS: Filters = { grades: [], categories: [], has_fsp: '', min_score: 0, skills: [], shortlisted: false }

export default function Matches() {
  const { jobId } = useParams()
  const toast = useToast()
  const [f, setF] = useState<Filters>(NO_FILTERS)
  const [refreshing, setRefreshing] = useState(false)
  const [showAllCats, setShowAllCats] = useState(false)
  const query = {
    grades: f.grades, categories: f.categories, has_fsp: f.has_fsp || undefined, min_score: f.min_score || undefined,
    skills: f.skills, shortlisted: f.shortlisted || undefined,
  }
  const { data, error, loading, reload, setData } = useApi<MatchList>(`/employer/requirements/${jobId}/matches`, query)
  const company = useApi<Company>('/employer/profile')
  const [invite, setInvite] = useState<CandidateCard | null>(null)
  const [compareIds, setCompareIds] = useState<number[]>([])
  const [compare, setCompare] = useState<CompareOut | null>(null)
  const [err, setErr] = useState<string | null>(null)

  if (loading && !data) return <Loading label="Ранжируем кандидатов…" />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  if (!data) return null
  const req = data.requirement
  const toggle = <K extends 'grades' | 'categories' | 'skills'>(k: K, v: string) =>
    setF({ ...f, [k]: f[k].includes(v) ? f[k].filter((x) => x !== v) : [...f[k], v] })
  const filtersOn = JSON.stringify(f) !== JSON.stringify(NO_FILTERS)
  // categories that really fit the need come first; the long tail of adjacent ones is collapsed
  const strongCats = data.categories.filter((c, i) => i < 3 || c.top_percent >= 60 || f.categories.includes(c.label))
  const hiddenCats = data.categories.length - strongCats.length

  const shortlist = async (c: CandidateCard) => {
    try {
      await api(`/employer/requirements/${jobId}/shortlist/${c.candidate_id}`, { method: 'POST', query: { value: !c.shortlisted } })
      setData({ ...data, items: data.items.map((x) => (x.candidate_id === c.candidate_id ? { ...x, shortlisted: !x.shortlisted } : x)) })
    } catch (e) {
      setErr(errorMessage(e))
    }
  }

  const doCompare = async () => {
    const [a, b] = compareIds
    const ia = data.items.find((x) => x.candidate_id === a)
    const ib = data.items.find((x) => x.candidate_id === b)
    const [hi, lo] = (ia?.match?.percent ?? 0) >= (ib?.match?.percent ?? 0) ? [a, b] : [b, a]
    try {
      setCompare(await api<CompareOut>(`/employer/requirements/${jobId}/compare`, { query: { a: hi, b: lo } }))
    } catch (e) {
      setErr(errorMessage(e))
    }
  }
  const refresh = async () => {
    setRefreshing(true)
    try {
      setData(await api<MatchList>(`/employer/requirements/${jobId}/matches`, { query: { ...query, refresh: true } }))
      toast('Подборка пересчитана')
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setRefreshing(false)
    }
  }
  const nameOf = (id: number) => data.items.find((x) => x.candidate_id === id)?.display_name ?? `#${id}`

  return (
    <div className="stack-lg">
      <div className="card" style={{ padding: 22 }}>
        <div className="row between wrap" style={{ alignItems: 'flex-start' }}>
          <div className="stack" style={{ gap: 8 }}>
            <Link to="/employer/requirements" className="small">← Все потребности</Link>
            <h1>{req.title}</h1>
            <div className="row wrap">
              <span className="badge violet">{req.specialization_name} · {req.grade_name}</span>
              <span className="badge outline">{salaryRange(req.salary_from, req.salary_to)}</span>
              <span className="badge outline">{WORK_FORMAT[req.work_format]}{req.city ? ` · ${req.city}` : ''}</span>
              {req.min_experience_years > 0 && <span className="badge outline">опыт {experienceFrom(req.min_experience_years)}</span>}
              {req.is_public && <span className="badge success">опубликована</span>}
            </div>
            <div className="row wrap">{req.skills.map((s) => <span key={s.slug} className={`chip ${s.importance === 'must' ? 'on' : ''}`}>{s.name}</span>)}</div>
          </div>
          <div className="row">
            <Link className="btn ghost" to={`/employer/requirements/${jobId}/edit`}><Pencil size={15} />Уточнить</Link>
            <button className="btn secondary" disabled={refreshing} onClick={refresh}><RefreshCcw size={15} />{refreshing ? 'Считаем…' : 'Пересчитать'}</button>
          </div>
        </div>
      </div>
      <ErrorBox error={err} />

      <div>
        <div className="row between wrap" style={{ marginBottom: 10 }}>
          <h3>Рекомендованные категории</h3><span className="small muted">{data.total} кандидатов в подборке · движок v{data.engine_version} · {ago(data.computed_at)}</span>
        </div>
        <div className="row wrap">
          {(showAllCats ? data.categories : strongCats).map((c) => (
            <button key={c.label} className={`chip selectable ${f.categories.includes(c.label) ? 'on' : ''}`} onClick={() => toggle('categories', c.label)}>
              <b>{c.label}</b> · {c.count} · ср. {c.avg_percent}% · макс. {c.top_percent}%</button>
          ))}
          {hiddenCats > 0 && (
            <button className="chip selectable" onClick={() => setShowAllCats(!showAllCats)}>
              {showAllCats ? 'Свернуть' : `ещё ${hiddenCats} смежных категорий`}</button>
          )}
        </div>
      </div>

      <div className="split-left">
        <div className="stack-lg sticky">
          <div className="card stack">
            <div className="row between"><h3 className="row"><SlidersHorizontal size={16} />Уточнить подборку</h3>
              {filtersOn && <button className="btn sm ghost" onClick={() => setF(NO_FILTERS)}>Сбросить</button>}</div>
            <p className="tiny muted">Фильтры применяются к сохранённой подборке — она не теряется.</p>
            <div className="field"><label>Грейд</label><div className="row wrap">
              {['junior', 'middle', 'senior'].map((g) => <button key={g} className={`chip selectable ${f.grades.includes(g) ? 'on' : ''}`} onClick={() => toggle('grades', g)}>{g[0].toUpperCase() + g.slice(1)}</button>)}</div></div>
            <div className="field"><label htmlFor="matches-f1">Достижения ФСП</label>
              <select id="matches-f1" className="select" value={f.has_fsp} onChange={(e) => setF({ ...f, has_fsp: e.target.value as Filters['has_fsp'] })}>
                <option value="">Не важно</option><option value="true">Есть подтверждённые</option><option value="false">Нет истории</option></select></div>
            <div className="field"><label htmlFor="matches-f2">Совпадение от {f.min_score}%</label>
              <input id="matches-f2" type="range" min={0} max={90} step={5} value={f.min_score} onChange={(e) => setF({ ...f, min_score: Number(e.target.value) })} style={{ accentColor: 'var(--primary)' }} /></div>
            <div className="field"><label>Обязательно владеет</label><div className="row wrap">
              {req.skills.map((s) => <button key={s.slug} className={`chip selectable ${f.skills.includes(s.slug) ? 'on' : ''}`} onClick={() => toggle('skills', s.slug)}>{s.name}</button>)}</div></div>
            <label className="check"><input type="checkbox" checked={f.shortlisted} onChange={(e) => setF({ ...f, shortlisted: e.target.checked })} /><span>Только избранные</span></label>
          </div>
          <div className="card stack">
            <h3>Как считается совпадение</h3>
            {data.weights.filter((w) => w.weight > 0).map((w) => (
              <div key={w.key} className="row between small"><span className="row"><i style={{ width: 10, height: 10, borderRadius: 3, background: COMPONENT_COLORS[w.key], display: 'inline-block' }} />{w.label}</span><b>{Math.round(w.weight * 100)}%</b></div>
            ))}
            <p className="tiny muted">Нет данных по фактору (например, ожиданий по зарплате) — его вес перераспределяется, без штрафа. Отсутствие ФСП = нейтральная база.</p>
          </div>
        </div>

        <div className="stack">
          {compareIds.length > 0 && (
            <div className="alert violet" style={{ alignItems: 'center' }}><ArrowLeftRight size={18} />
              <span style={{ flex: 1 }}>Для сравнения: {compareIds.map(nameOf).join(' и ')}{compareIds.length < 2 && ' — выберите ещё одного'}</span>
              <button className="btn sm" disabled={compareIds.length < 2} onClick={doCompare}>Почему A выше B?</button>
              <button className="btn sm ghost" onClick={() => setCompareIds([])}>Сбросить</button></div>
          )}
          <div className="row between"><span className="small muted">Показано {data.items.length} из {data.filtered}{data.filtered !== data.total ? ` (всего в подборке ${data.total})` : ''}</span></div>
          {data.items.length === 0 ? (
            <div className="card"><Empty icon={<Users size={26} />} title="Под фильтры никто не подходит"
              text={data.total ? 'Ослабьте фильтры — подборка сохранена.' : 'В базе пока нет подтверждённых кандидатов этой специализации. Попробуйте смежный грейд или стек.'}
              action={filtersOn ? <button className="btn secondary" onClick={() => setF(NO_FILTERS)}>Сбросить фильтры</button> : undefined} /></div>
          ) : data.items.map((c) => (
            <div key={c.candidate_id} className="cand">
              <div className="stack" style={{ alignItems: 'center', gap: 6 }}>
                <ScoreRing value={c.match?.percent ?? 0} size={78} />
                <span className="rank">#{c.match?.rank}</span>
              </div>
              <div className="stack" style={{ gap: 8, minWidth: 0 }}>
                <div className="row wrap">
                  <Avatar name={c.display_name} />
                  <div><div className="name">{c.display_name}</div>
                    <div className="small muted">{c.headline} · {years(c.experience_years)} · {c.city ?? '—'} · {WORK_FORMAT[c.work_format]}{c.expected_salary ? ` · ожидания ${rub(c.expected_salary)}` : ''}</div></div>
                </div>
                <div className="row wrap"><CategoryBadge category={c.category} /><span className="badge outline">Тест {c.category?.scaled_score}/100</span><FspSummary fsp={c.fsp} compact />
                  {c.last_active_days != null && <span className="badge muted">{activeAgo(c.last_active_days)}</span>}</div>
                {c.match && <SkillMatchChips items={c.match.skill_matches} />}
                {c.match && <Reasons reasons={c.match.reasons} limit={4} />}
                {c.match && <MatchBreakdown components={c.match.components} />}
              </div>
              <div className="actions">
                {c.invitation_status ? <InvitationStatusBadge status={c.invitation_status} /> : null}
                {c.applied && <span className="badge info">откликнулся сам</span>}
                <Link className="btn secondary sm" to={`/employer/candidates/${c.candidate_id}?requirement_id=${jobId}`}>Профиль и объяснение<ChevronRight size={14} /></Link>
                {c.invitation_status === 'sent' || c.invitation_status === 'viewed'
                  ? <button className="btn sm" disabled title="Ждём ответа кандидата"><Send size={14} />Приглашение отправлено</button>
                  : <button className="btn sm" onClick={() => setInvite(c)}><Send size={14} />Пригласить</button>}
                <div className="row">
                  <button className="btn sm ghost" style={{ flex: 1 }} onClick={() => shortlist(c)} title="В избранное">
                    <Star size={14} fill={c.shortlisted ? 'var(--gold)' : 'none'} color={c.shortlisted ? 'var(--gold)' : 'currentColor'} /></button>
                  <button className={`btn sm ${compareIds.includes(c.candidate_id) ? 'secondary' : 'ghost'}`} style={{ flex: 1 }} title="Сравнить"
                    onClick={() => setCompareIds(compareIds.includes(c.candidate_id) ? compareIds.filter((x) => x !== c.candidate_id) : [...compareIds.slice(-1), c.candidate_id])}>
                    <ArrowLeftRight size={14} /></button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {invite && (
        <InviteModal candidateId={invite.candidate_id} candidateName={invite.display_name} requirement={req}
          defaultContact={[company.data?.contact_telegram, company.data?.contact_email].filter(Boolean).join(' · ')}
          onClose={() => setInvite(null)}
          onSent={() => { setInvite(null); toast('Приглашение отправлено'); void reload() }} />
      )}
      {compare && (
        <Modal title="Почему один кандидат выше другого" onClose={() => setCompare(null)} wide>
          <div className="row between wrap">
            <div className="row"><ScoreRing value={compare.a.percent} size={64} /><b>{nameOf(compare.a.candidate_id)}</b></div>
            <span className="badge violet">{compare.delta_percent >= 0 ? '+' : ''}{compare.delta_percent} п.</span>
            <div className="row"><b>{nameOf(compare.b.candidate_id)}</b><ScoreRing value={compare.b.percent} size={64} /></div>
          </div>
          <div className="alert info" style={{ marginTop: 14 }}>{compare.summary}</div>
          <table className="table" style={{ marginTop: 10 }}>
            <thead><tr><th>Фактор</th><th>{nameOf(compare.a.candidate_id)}</th><th>{nameOf(compare.b.candidate_id)}</th><th>Разница</th></tr></thead>
            <tbody>{compare.a.components.map((ca) => {
              const cb = compare.b.components.find((x) => x.key === ca.key)!
              const d = ca.contribution - cb.contribution
              return (
                <tr key={ca.key}><td>{ca.label}</td><td>{ca.available ? `${ca.contribution.toFixed(1)} · ${ca.detail}` : '—'}</td>
                  <td>{cb.available ? `${cb.contribution.toFixed(1)} · ${cb.detail}` : '—'}</td>
                  <td className="bold" style={{ color: d > 0.05 ? 'var(--success)' : d < -0.05 ? 'var(--danger)' : 'var(--muted)' }}>{d > 0 ? '+' : ''}{d.toFixed(1)}</td></tr>
              )
            })}</tbody>
          </table>
        </Modal>
      )}
    </div>
  )
}
