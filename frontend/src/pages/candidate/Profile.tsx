import { FileUp, Printer, Save, ShieldCheck, Sparkles } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { CandidateProfile, ResumeParseOut } from '../../api/types'
import { SkillLevelEditor, type SkillLevel } from '../../components/SkillPicker'
import { CategoryBadge, ErrorBox, Loading, useToast } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { WORK_FORMATS, workFormatKey } from '../../lib/format'
import { useReference } from '../../lib/reference'

interface Form {
  first_name: string; last_name: string; phone: string; telegram: string; city: string; headline: string
  about: string; experience_years: number; education: string; expected_salary: string; work_format: string
  specialization_id: string; declared_grade_id: string; team_roles: string; soft_skills: string
}

const toForm = (p: CandidateProfile): Form => ({
  first_name: p.first_name, last_name: p.last_name, phone: p.phone ?? '', telegram: p.telegram ?? '', city: p.city ?? '',
  headline: p.headline, about: p.about, experience_years: p.experience_years, education: p.education ?? '',
  expected_salary: p.expected_salary ? String(p.expected_salary) : '', work_format: p.work_format,
  specialization_id: p.specialization_id ?? '', declared_grade_id: p.declared_grade_id ?? '',
  team_roles: p.team_roles.join(', '), soft_skills: p.soft_skills.join(', '),
})

const splitList = (s: string) => s.split(',').map((x) => x.trim()).filter(Boolean)

export default function ProfilePage() {
  const { data, error, loading, setData } = useApi<CandidateProfile>('/candidate/profile')
  const { ref, specName, gradeName } = useReference()
  const { t, fmt } = useI18n()
  const toast = useToast()
  const [form, setForm] = useState<Form | null>(null)
  const [skills, setSkills] = useState<SkillLevel[]>([])
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState<string | null>(null)
  const [parsed, setParsed] = useState<ResumeParseOut | null>(null)
  const [parsing, setParsing] = useState(false)

  useEffect(() => {
    if (data) {
      setForm(toForm(data))
      setSkills(data.skills.map((s) => ({ slug: s.slug, level: s.level, years: s.years })))
    }
  }, [data])

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} />
  if (!data || !form) return null

  const set = (k: keyof Form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })
  const verifiedSkills = new Map(data.skills.map((s) => [s.slug, s]))

  const save = async (e: FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setSaveError(null)
    try {
      const p = await api<CandidateProfile>('/candidate/profile', {
        method: 'PUT',
        body: {
          first_name: form.first_name, last_name: form.last_name, phone: form.phone || null, telegram: form.telegram || null,
          city: form.city || null, headline: form.headline, about: form.about, experience_years: Number(form.experience_years) || 0,
          education: form.education || null, expected_salary: form.expected_salary ? Number(form.expected_salary) : null,
          work_format: form.work_format, specialization_id: form.specialization_id || null,
          declared_grade_id: form.declared_grade_id || null, team_roles: splitList(form.team_roles),
          soft_skills: splitList(form.soft_skills), skills,
        },
      })
      setData(p)
      toast(t('cand.profile.saved'))
    } catch (err) {
      setSaveError(errorMessage(err))
    } finally {
      setSaving(false)
    }
  }

  const upload = async (file: File) => {
    setParsing(true)
    setSaveError(null)
    const fd = new FormData()
    fd.append('file', file)
    try {
      setParsed(await api<ResumeParseOut>('/candidate/resume/parse', { method: 'POST', form: fd }))
    } catch (err) {
      setSaveError(errorMessage(err))
    } finally {
      setParsing(false)
    }
  }

  const applyParsed = () => {
    if (!parsed) return
    setForm({
      ...form,
      first_name: parsed.first_name ?? form.first_name, last_name: parsed.last_name ?? form.last_name,
      phone: parsed.phone ?? form.phone, telegram: parsed.telegram ?? form.telegram,
      specialization_id: parsed.specialization_id ?? form.specialization_id,
      declared_grade_id: parsed.declared_grade_id ?? form.declared_grade_id,
      experience_years: parsed.experience_years ?? form.experience_years,
      work_format: parsed.work_format ?? form.work_format,
      expected_salary: parsed.expected_salary ? String(parsed.expected_salary) : form.expected_salary,
    })
    const have = new Set(skills.map((s) => s.slug))
    setSkills([...skills, ...parsed.skills.filter((s) => !have.has(s.slug)).map((s) => ({ slug: s.slug, level: 3, years: 1 }))])
    setParsed(null)
    toast(t('cand.profile.parsedApplied'))
  }

  const parsedSummary = parsed ? [
    parsed.last_name && t('cand.profile.parsed.name', { value: `${parsed.last_name} ${parsed.first_name ?? ''}`.trim() }),
    parsed.email && t('cand.profile.parsed.email', { value: parsed.email }),
    parsed.phone && t('cand.profile.parsed.phone', { value: parsed.phone }),
    parsed.telegram && t('cand.profile.parsed.telegram', { value: parsed.telegram }),
    parsed.specialization_id && t('cand.profile.parsed.spec', { value: specName(parsed.specialization_id) }),
    parsed.declared_grade_id && t('cand.profile.parsed.grade', { value: gradeName(parsed.declared_grade_id) }),
    parsed.experience_years && t('cand.profile.parsed.experience', { value: fmt.years(parsed.experience_years) }),
  ].filter(Boolean).join(' · ') : ''

  return (
    <form onSubmit={save} className="stack-lg">
      <div className="page-head">
        <div><h1>{t('nav.profile')}</h1><p className="sub">{t('cand.profile.sub')}</p></div>
        <div className="row"><Link className="btn ghost" to="/candidate/print"><Printer size={16} />{t('cand.profile.pdf')}</Link>
          <button className="btn" disabled={saving}><Save size={16} />{saving ? t('common.saving') : t('common.save')}</button></div>
      </div>
      <ErrorBox error={saveError} />

      <div className="card" style={{ background: 'var(--primary-50)', borderColor: 'var(--primary-100)' }}>
        <div className="row between wrap">
          <div className="row"><Sparkles size={20} color="var(--primary)" />
            <div><div className="bold">{t('cand.profile.fromPdf')}</div><div className="small muted">{t('cand.profile.fromPdfHint')}</div></div></div>
          <label className="btn secondary" style={{ cursor: 'pointer' }}><FileUp size={16} />{parsing ? t('cand.profile.parsing') : t('cand.profile.uploadPdf')}
            <input type="file" accept="application/pdf" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} /></label>
        </div>
        {parsed && (
          <div className="card" style={{ marginTop: 14 }}>
            <div className="bold">{t('cand.profile.foundIn', { file: parsed.filename })}</div>
            <div className="small" style={{ marginTop: 8 }}>{parsedSummary || t('cand.profile.noContacts')}</div>
            <div className="row wrap" style={{ marginTop: 8 }}>{parsed.skills.map((s) => <span key={s.slug} className="chip">{s.name}</span>)}</div>
            <div className="row" style={{ marginTop: 12 }}><button type="button" className="btn sm" onClick={applyParsed}>{t('cand.profile.apply')}</button>
              <button type="button" className="btn sm ghost" onClick={() => setParsed(null)}>{t('common.cancel')}</button></div>
          </div>
        )}
      </div>

      <div className="split">
        <div className="stack-lg">
          <div className="card stack-lg">
            <h3>{t('cand.profile.personal')}</h3>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="profile-f1">{t('auth.firstName')}</label><input id="profile-f1" className="input" value={form.first_name} onChange={set('first_name')} /></div>
              <div className="field"><label htmlFor="profile-f2">{t('auth.lastName')}</label><input id="profile-f2" className="input" value={form.last_name} onChange={set('last_name')} /></div>
              <div className="field"><label htmlFor="profile-f3">{t('cand.profile.phone')}</label><input id="profile-f3" className="input" value={form.phone} onChange={set('phone')} placeholder="+7 900 000-00-00" /></div>
              <div className="field"><label htmlFor="profile-f4">Telegram</label><input id="profile-f4" className="input" value={form.telegram} onChange={set('telegram')} placeholder="@username" /></div>
              <div className="field"><label htmlFor="profile-f5">{t('cand.profile.city')}</label><input id="profile-f5" className="input" value={form.city} onChange={set('city')} /></div>
              <div className="field"><label htmlFor="profile-f6">{t('auth.email')}</label><input id="profile-f6" className="input" value={data.email} disabled /></div>
            </div>
            <p className="small muted"><ShieldCheck size={14} style={{ verticalAlign: -2 }} /> {t('cand.profile.contactsNote')}</p>
          </div>

          <div className="card stack-lg">
            <h3>{t('cand.profile.cv')}</h3>
            <div className="field"><label htmlFor="profile-f7">{t('cand.profile.headline')}</label><input id="profile-f7" className="input" value={form.headline} onChange={set('headline')} placeholder={t('cand.profile.headlinePlaceholder')} /></div>
            <div className="field"><label htmlFor="profile-f8">{t('cand.profile.about')}</label><textarea id="profile-f8" className="textarea" value={form.about} onChange={set('about')} placeholder={t('cand.profile.aboutPlaceholder')} /></div>
            <div className="grid grid-3">
              <div className="field"><label htmlFor="profile-f9">{t('cand.profile.experience')}</label><input id="profile-f9" className="input" type="number" min={0} max={50} step="any" value={form.experience_years} onChange={set('experience_years')} /></div>
              <div className="field"><label htmlFor="profile-f10">{t('cand.profile.salary')}</label><input id="profile-f10" className="input" type="number" min={0} step="any" value={form.expected_salary} onChange={set('expected_salary')} /></div>
              <div className="field"><label htmlFor="profile-f11">{t('cand.profile.format')}</label>
                <select id="profile-f11" className="select" value={form.work_format} onChange={set('work_format')}>
                  {WORK_FORMATS.map((k) => <option key={k} value={k}>{t(workFormatKey(k))}</option>)}</select></div>
            </div>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="profile-f12">{t('cand.profile.roles')}</label><input id="profile-f12" className="input" value={form.team_roles} onChange={set('team_roles')} placeholder={t('cand.profile.rolesPlaceholder')} /><span className="hint">{t('cand.profile.commaSeparated')}</span></div>
              <div className="field"><label htmlFor="profile-f13">{t('cand.profile.softSkills')}</label><input id="profile-f13" className="input" value={form.soft_skills} onChange={set('soft_skills')} placeholder={t('cand.profile.softSkillsPlaceholder')} /></div>
            </div>
            <div className="field"><label htmlFor="profile-f14">{t('cand.profile.education')}</label><input id="profile-f14" className="input" value={form.education} onChange={set('education')} /></div>
          </div>

          <div className="card stack-lg">
            <div className="card-title" style={{ marginBottom: 0 }}><h3>{t('cand.profile.skills')}</h3><span className="small muted">{t('cand.profile.skillsCount', { n: skills.length })}</span></div>
            <SkillLevelEditor value={skills} onChange={setSkills} specialization={form.specialization_id} />
            {data.skills.some((s) => s.verified) && (
              <div className="row wrap"><span className="small muted">{t('cand.profile.verifiedSkills')}</span>
                {data.skills.filter((s) => s.verified).map((s) => <span key={s.slug} className="chip verified"><ShieldCheck size={12} />{s.name} · {verifiedSkills.get(s.slug)?.competency_score}%</span>)}</div>
            )}
          </div>
        </div>

        <div className="stack-lg sticky">
          <div className="card stack">
            <h3>{t('cand.profile.survey')}</h3>
            <p className="small muted">{t('cand.profile.surveyHint')}</p>
            <div className="field"><label htmlFor="profile-f15">{t('cand.profile.industry')}</label><input id="profile-f15" className="input" value={t('cand.profile.industryIt')} disabled /></div>
            <div className="field"><label htmlFor="profile-f16">{t('cand.profile.spec')}</label>
              <select id="profile-f16" className="select" value={form.specialization_id} onChange={set('specialization_id')}>
                <option value="">{t('cand.profile.choose')}</option>{ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
            <div className="field"><label htmlFor="profile-f17">{t('cand.profile.declaredGrade')}</label>
              <select id="profile-f17" className="select" value={form.declared_grade_id} onChange={set('declared_grade_id')}>
                <option value="">{t('cand.profile.choose')}</option>{ref?.grades.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
          </div>
          <div className="card stack">
            <h3>{t('cand.profile.category')}</h3>
            <CategoryBadge category={data.category} />
            <Link to="/candidate/testing" className="btn secondary sm">{t('cand.profile.toTesting')}</Link>
          </div>
          <div className="card stack">
            <h3>{t('cand.profile.completeness', { n: data.completeness.percent })}</h3>
            <div className="bar"><i style={{ width: `${data.completeness.percent}%` }} /></div>
            {data.completeness.missing.map((m) => <div key={m.key} className="small muted">• {m.title}</div>)}
          </div>
        </div>
      </div>
    </form>
  )
}
