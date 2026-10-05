import { Printer } from 'lucide-react'
import { useApi } from '../../api/hooks'
import type { CandidateProfile, FSPOut } from '../../api/types'
import { AchievementList, CategoryBadge, CompetencyBars, ErrorBox, Loading, ScoreScale } from '../../components/ui'
import { date, rub, WORK_FORMAT, years } from '../../lib/format'
import { useReference } from '../../lib/reference'

/** Standardized profile: print → "Save as PDF". */
export default function PrintProfile() {
  const p = useApi<CandidateProfile>('/candidate/profile')
  const f = useApi<FSPOut>('/candidate/fsp')
  const { specName, gradeName } = useReference()
  if (p.loading && !p.data) return <Loading />
  if (p.error) return <ErrorBox error={p.error} />
  if (!p.data) return null
  const d = p.data
  return (
    <div className="stack-lg" style={{ maxWidth: 860 }}>
      <div className="row between no-print"><h1>Стандартизированный профиль</h1>
        <button className="btn" onClick={() => window.print()}><Printer size={16} />Сохранить в PDF</button></div>
      <div className="card" style={{ padding: 30 }}>
        <div className="row between wrap">
          <div><h1 style={{ fontSize: 26 }}>{d.first_name} {d.last_name}</h1><div className="muted">{d.headline} · {d.city ?? '—'}</div></div>
          <CategoryBadge category={d.category} size="lg" />
        </div>
        <div className="divider" />
        <dl className="kv">
          <dt>Специализация (опрос)</dt><dd>{specName(d.specialization_id)} · заявлен {gradeName(d.declared_grade_id)}</dd>
          <dt>Подтверждённый грейд</dt><dd>{d.category ? `${d.category.grade_name} · ${date(d.category.verified_at)}` : 'не подтверждён'}</dd>
          <dt>Опыт</dt><dd>{years(d.experience_years)}</dd>
          <dt>Формат</dt><dd>{WORK_FORMAT[d.work_format]}</dd>
          <dt>Ожидания</dt><dd>{rub(d.expected_salary)}</dd>
          <dt>Контакты</dt><dd>{d.email}{d.phone ? ` · ${d.phone}` : ''}{d.telegram ? ` · ${d.telegram}` : ''}</dd>
          {d.education && <><dt>Образование</dt><dd>{d.education}</dd></>}
        </dl>
        {d.category?.scaled_score != null && <div style={{ marginTop: 18 }}><ScoreScale score={d.category.scaled_score} /></div>}
        <h3 style={{ marginTop: 22 }}>О себе</h3><p style={{ marginTop: 6 }}>{d.about || '—'}</p>
        <h3 style={{ marginTop: 22 }}>Навыки</h3>
        <div className="row wrap" style={{ marginTop: 8 }}>{d.skills.map((s) => <span key={s.slug} className={`chip ${s.verified ? 'verified' : ''}`}>{s.name} · {s.level}/5</span>)}</div>
        <h3 style={{ marginTop: 22 }}>Компетенции по результатам теста</h3>
        <div style={{ marginTop: 10 }}><CompetencyBars items={d.competencies} /></div>
        <h3 style={{ marginTop: 22 }}>Достижения ФСП</h3>
        <div style={{ marginTop: 8 }}>{f.data?.profile?.achievements.length ? <AchievementList items={f.data.profile.achievements} /> : <p className="muted">Истории ФСП нет.</p>}</div>
        <p className="tiny muted" style={{ marginTop: 24 }}>Сформировано FSP Talent {date(new Date().toISOString())}. Категория подтверждена тестированием платформы.</p>
      </div>
    </div>
  )
}
