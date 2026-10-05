import { Printer } from 'lucide-react'
import { useApi } from '../../api/hooks'
import type { CandidateProfile, FSPOut } from '../../api/types'
import { AchievementList, CategoryBadge, CompetencyBars, ErrorBox, Loading, ScoreScale } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { workFormatKey } from '../../lib/format'
import { useReference } from '../../lib/reference'

/** Standardized profile: print → "Save as PDF" (in the current interface language). */
export default function PrintProfile() {
  const p = useApi<CandidateProfile>('/candidate/profile')
  const f = useApi<FSPOut>('/candidate/fsp')
  const { specName, gradeName } = useReference()
  const { t, fmt } = useI18n()
  if (p.loading && !p.data) return <Loading />
  if (p.error) return <ErrorBox error={p.error} />
  if (!p.data) return null
  const d = p.data
  return (
    <div className="stack-lg" style={{ maxWidth: 860 }}>
      <div className="row between no-print"><h1>{t('cand.print.title')}</h1>
        <button className="btn" onClick={() => window.print()}><Printer size={16} />{t('cand.print.save')}</button></div>
      <div className="card" style={{ padding: 30 }}>
        <div className="row between wrap">
          <div><h1 style={{ fontSize: 26 }}>{d.first_name} {d.last_name}</h1><div className="muted">{d.headline} · {d.city ?? '—'}</div></div>
          <CategoryBadge category={d.category} size="lg" />
        </div>
        <div className="divider" />
        <dl className="kv">
          <dt>{t('cand.print.spec')}</dt><dd>{t('cand.print.specValue', { spec: specName(d.specialization_id), grade: gradeName(d.declared_grade_id) })}</dd>
          <dt>{t('cand.print.grade')}</dt><dd>{d.category ? `${d.category.grade_name} · ${fmt.date(d.category.verified_at)}` : t('cand.print.notVerified')}</dd>
          <dt>{t('cand.print.experience')}</dt><dd>{fmt.years(d.experience_years)}</dd>
          <dt>{t('cand.print.format')}</dt><dd>{t(workFormatKey(d.work_format))}</dd>
          <dt>{t('cand.print.salary')}</dt><dd>{fmt.money(d.expected_salary)}</dd>
          <dt>{t('cand.print.contacts')}</dt><dd>{d.email}{d.phone ? ` · ${d.phone}` : ''}{d.telegram ? ` · ${d.telegram}` : ''}</dd>
          {d.education && <><dt>{t('cand.profile.education')}</dt><dd>{d.education}</dd></>}
        </dl>
        {d.category?.scaled_score != null && <div style={{ marginTop: 18 }}><ScoreScale score={d.category.scaled_score} /></div>}
        <h3 style={{ marginTop: 22 }}>{t('cand.profile.about')}</h3><p style={{ marginTop: 6 }}>{d.about || '—'}</p>
        <h3 style={{ marginTop: 22 }}>{t('cand.print.skills')}</h3>
        <div className="row wrap" style={{ marginTop: 8 }}>{d.skills.map((s) => <span key={s.slug} className={`chip ${s.verified ? 'verified' : ''}`}>{s.name} · {s.level}/5</span>)}</div>
        <h3 style={{ marginTop: 22 }}>{t('cand.print.competencies')}</h3>
        <div style={{ marginTop: 10 }}><CompetencyBars items={d.competencies} /></div>
        <h3 style={{ marginTop: 22 }}>{t('nav.fsp')}</h3>
        <div style={{ marginTop: 8 }}>{f.data?.profile?.achievements.length ? <AchievementList items={f.data.profile.achievements} />
          : <p className="muted">{t('cand.print.noFsp')}</p>}</div>
        <p className="tiny muted" style={{ marginTop: 24 }}>{t('cand.print.footer', { date: fmt.date(new Date().toISOString()) })}</p>
      </div>
    </div>
  )
}
