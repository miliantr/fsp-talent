import { Sparkles, Wand2 } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { ParseNeedOut, Requirement } from '../../api/types'
import { SkillSelect } from '../../components/SkillPicker'
import { ErrorBox, Loading, Switch } from '../../components/ui'
import { useI18n } from '../../i18n/context'
import { WORK_FORMATS, workFormatKey } from '../../lib/format'
import { useReference } from '../../lib/reference'

const EMPTY = {
  title: '', description: '', team_description: '', specialization_id: 'backend', grade_id: 'middle',
  must_skills: [] as string[], nice_skills: [] as string[], salary_from: '', salary_to: '', work_format: 'any',
  city: '', min_experience_years: '0', weights_preset: 'balanced', is_public: false,
}

export default function RequirementForm() {
  const { jobId } = useParams()
  const nav = useNavigate()
  const { t } = useI18n()
  const { ref, specName, gradeName } = useReference()
  const existing = useApi<Requirement>(jobId ? `/employer/requirements/${jobId}` : null)
  const [form, setForm] = useState(EMPTY)
  const [text, setText] = useState('')
  const [busy, setBusy] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [hint, setHint] = useState<string | null>(null)

  useEffect(() => {
    const r = existing.data
    if (!r) return
    setForm({
      title: r.title, description: r.description, team_description: r.team_description, specialization_id: r.specialization_id,
      grade_id: r.grade_id, must_skills: r.skills.filter((s) => s.importance === 'must').map((s) => s.slug),
      nice_skills: r.skills.filter((s) => s.importance === 'nice').map((s) => s.slug), salary_from: String(r.salary_from),
      salary_to: String(r.salary_to), work_format: r.work_format, city: r.city ?? '', min_experience_years: String(r.min_experience_years),
      weights_preset: r.weights_preset, is_public: r.is_public,
    })
  }, [existing.data])

  if (jobId && existing.loading && !existing.data) return <Loading />
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  const parse = async () => {
    setParsing(true)
    setErr(null)
    try {
      const p = await api<ParseNeedOut>('/employer/requirements/parse', { method: 'POST', body: { text } })
      const must = p.skills.filter((s) => s.importance !== 'nice').map((s) => s.slug)
      const nice = p.skills.filter((s) => s.importance === 'nice').map((s) => s.slug)
      setForm((f) => ({
        ...f,
        description: f.description || text,
        specialization_id: p.specialization_id ?? f.specialization_id,
        grade_id: p.grade_id ?? f.grade_id,
        must_skills: Array.from(new Set([...f.must_skills, ...must.slice(0, 6)])),
        nice_skills: Array.from(new Set([...f.nice_skills, ...must.slice(6), ...nice].filter((s) => !f.must_skills.includes(s)))),
        salary_from: p.salary_from ? String(p.salary_from) : f.salary_from,
        salary_to: p.salary_to ? String(p.salary_to) : f.salary_to,
        work_format: p.work_format ?? f.work_format,
        min_experience_years: p.min_experience_years != null ? String(p.min_experience_years) : f.min_experience_years,
        title: f.title || `${specName(p.specialization_id ?? f.specialization_id)} ${gradeName(p.grade_id ?? f.grade_id)}`,
      }))
      const found = [
        p.specialization_id && specName(p.specialization_id), p.grade_id && gradeName(p.grade_id),
        p.skills.length && t('emp.form.foundSkills', { n: p.skills.length }), p.salary_from && t('emp.form.foundSalary'),
        p.work_format && t(workFormatKey(p.work_format)),
      ].filter(Boolean).join(', ')
      setHint(t('emp.form.recognized', { items: found || t('emp.form.nothing') }))
    } catch (e) {
      setErr(errorMessage(e))
    } finally {
      setParsing(false)
    }
  }

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const from = Number(form.salary_from)
    const to = Number(form.salary_to)
    if (!from || !to) return setErr(t('emp.form.salaryRequired'))
    if (to < from) return setErr(t('invite.salaryInverted'))
    setBusy(true)
    setErr(null)
    try {
      const body = { ...form, salary_from: from, salary_to: to, min_experience_years: Number(form.min_experience_years) || 0, city: form.city || null }
      const r = await api<Requirement>(jobId ? `/employer/requirements/${jobId}` : '/employer/requirements', { method: jobId ? 'PUT' : 'POST', body })
      nav(`/employer/requirements/${r.id}`)
    } catch (ex) {
      setErr(errorMessage(ex))
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="stack-lg" onSubmit={submit}>
      <div className="page-head"><div><h1>{jobId ? t('emp.form.editTitle') : t('emp.form.title')}</h1>
        <p className="sub">{t('emp.form.sub')}</p></div>
        <button className="btn lg" disabled={busy}><Sparkles size={18} />{busy ? t('emp.form.busy') : jobId ? t('emp.form.saveAndRecompute') : t('emp.form.submit')}</button></div>
      <ErrorBox error={err} />

      {!jobId && (
        <div className="card" style={{ background: 'var(--primary-50)', borderColor: 'var(--primary-100)' }}>
          <div className="row"><Wand2 size={18} color="var(--primary)" /><b>{t('emp.form.freeText')}</b><span className="small muted">{t('emp.form.freeTextHint')}</span></div>
          <textarea className="textarea" style={{ marginTop: 10, minHeight: 80 }} value={text} onChange={(e) => setText(e.target.value)}
            placeholder={t('emp.form.freeTextPlaceholder')} aria-label={t('emp.form.freeText')} />
          <div className="row" style={{ marginTop: 10 }}><button type="button" className="btn secondary sm" onClick={parse} disabled={parsing || text.trim().length < 10}>
            <Wand2 size={14} />{parsing ? t('emp.form.parsing') : t('emp.form.parse')}</button>{hint && <span className="small">{hint}</span>}</div>
        </div>
      )}

      <div className="split">
        <div className="stack-lg">
          <div className="card stack-lg">
            <div className="field"><label htmlFor="requirementform-f1">{t('emp.form.position')}</label>
              <input id="requirementform-f1" className="input" required minLength={3} value={form.title} onChange={set('title')} placeholder="Backend Developer" /></div>
            <div className="grid grid-2">
              <div className="field"><label>{t('cand.profile.spec')}</label><div className="row wrap">
                {ref?.specializations.map((s) => <button type="button" key={s.id} className={`chip selectable ${form.specialization_id === s.id ? 'on' : ''}`} onClick={() => setForm({ ...form, specialization_id: s.id })}>{s.name}</button>)}</div></div>
              <div className="field"><label>{t('emp.match.grade')}</label><div className="row wrap">
                {ref?.grades.map((g) => <button type="button" key={g.id} className={`chip selectable ${form.grade_id === g.id ? 'on' : ''}`} onClick={() => setForm({ ...form, grade_id: g.id })}>{g.name}</button>)}</div></div>
            </div>
            <div className="field"><label>{t('emp.form.must')}</label>
              <SkillSelect value={form.must_skills} onChange={(v) => setForm({ ...form, must_skills: v })} specialization={form.specialization_id} placeholder={t('emp.form.mustPlaceholder')} />
              <span className="hint">{t('emp.form.mustHint')}</span></div>
            <div className="field"><label>{t('emp.form.nice')}</label>
              <SkillSelect value={form.nice_skills} onChange={(v) => setForm({ ...form, nice_skills: v })} specialization={form.specialization_id} /></div>
          </div>
          <div className="card stack-lg">
            <div className="field"><label htmlFor="requirementform-f2">{t('emp.form.duties')}</label><textarea id="requirementform-f2" className="textarea" value={form.description} onChange={set('description')} /></div>
            <div className="field"><label htmlFor="requirementform-f3">{t('emp.form.team')}</label><textarea id="requirementform-f3" className="textarea" style={{ minHeight: 80 }} value={form.team_description} onChange={set('team_description')} placeholder={t('emp.form.teamPlaceholder')} /></div>
          </div>
        </div>
        <div className="stack-lg sticky">
          <div className="card stack">
            <h3>{t('emp.form.terms')}</h3>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="requirementform-f4">{t('invite.salaryFrom')}</label><input id="requirementform-f4" className="input" type="number" required min={1} step="any" value={form.salary_from} onChange={set('salary_from')} /></div>
              <div className="field"><label htmlFor="requirementform-f5">{t('invite.salaryTo')}</label><input id="requirementform-f5" className="input" type="number" required min={1} step="any" value={form.salary_to} onChange={set('salary_to')} /></div>
            </div>
            <span className="hint small muted">{t('emp.form.salaryHint')}</span>
            <div className="field"><label htmlFor="requirementform-f6">{t('invite.format')}</label><select id="requirementform-f6" className="select" value={form.work_format} onChange={set('work_format')}>
              {WORK_FORMATS.map((k) => <option key={k} value={k}>{t(workFormatKey(k))}</option>)}</select></div>
            <div className="field"><label htmlFor="requirementform-f7">{t('cand.profile.city')}</label><input id="requirementform-f7" className="input" value={form.city} onChange={set('city')} /></div>
            <div className="field"><label htmlFor="requirementform-f8">{t('emp.form.minExperience')}</label><input id="requirementform-f8" className="input" type="number" min={0} max={30} step="any" value={form.min_experience_years} onChange={set('min_experience_years')} /></div>
          </div>
          <div className="card stack">
            <h3>{t('emp.form.strategy')}</h3>
            {ref?.weight_presets.map((p) => (
              <label key={p.id} className="check"><input type="radio" name="preset" checked={form.weights_preset === p.id} onChange={() => setForm({ ...form, weights_preset: p.id })} />
                <span><b>{p.label}</b><span className="tiny muted" style={{ display: 'block' }}>
                  {Object.entries(p.weights).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([k, v]) => `${ref.component_labels[k]} ${Math.round(v * 100)}%`).join(' · ')}</span></span></label>
            ))}
          </div>
          <div className="card"><Switch checked={form.is_public} onChange={(v) => setForm({ ...form, is_public: v })} label={t('emp.form.publish')} hint={t('emp.form.publishHint')} /></div>
        </div>
      </div>
    </form>
  )
}
