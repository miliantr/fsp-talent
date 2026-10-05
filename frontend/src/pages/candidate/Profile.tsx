import { FileUp, Printer, Save, ShieldCheck, Sparkles } from 'lucide-react'
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, errorMessage } from '../../api/client'
import { useApi } from '../../api/hooks'
import type { CandidateProfile, ResumeParseOut } from '../../api/types'
import { SkillLevelEditor, type SkillLevel } from '../../components/SkillPicker'
import { CategoryBadge, ErrorBox, Loading, useToast } from '../../components/ui'
import { WORK_FORMAT } from '../../lib/format'
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
  const { ref } = useReference()
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
      toast('Профиль сохранён')
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
    toast('Данные из резюме подставлены — проверьте и сохраните')
  }

  return (
    <form onSubmit={save} className="stack-lg">
      <div className="page-head">
        <div><h1>Профиль и резюме</h1><p className="sub">Резюме дополняет профиль, но категорию определяет только тест. Контакты скрыты от работодателей до вашего согласия.</p></div>
        <div className="row"><Link className="btn ghost" to="/candidate/print"><Printer size={16} />PDF-профиль</Link>
          <button className="btn" disabled={saving}><Save size={16} />{saving ? 'Сохраняем…' : 'Сохранить'}</button></div>
      </div>
      <ErrorBox error={saveError} />

      <div className="card" style={{ background: 'var(--primary-50)', borderColor: 'var(--primary-100)' }}>
        <div className="row between wrap">
          <div className="row"><Sparkles size={20} color="var(--primary)" />
            <div><div className="bold">Заполнить из PDF-резюме</div><div className="small muted">Распознаем ФИО, контакты, стек, грейд, стаж — вы проверите перед сохранением</div></div></div>
          <label className="btn secondary" style={{ cursor: 'pointer' }}><FileUp size={16} />{parsing ? 'Распознаём…' : 'Загрузить PDF'}
            <input type="file" accept="application/pdf" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} /></label>
        </div>
        {parsed && (
          <div className="card" style={{ marginTop: 14 }}>
            <div className="bold">Найдено в «{parsed.filename}»</div>
            <div className="small" style={{ marginTop: 8 }}>
              {[parsed.last_name && `ФИО: ${parsed.last_name} ${parsed.first_name ?? ''}`, parsed.email && `e-mail: ${parsed.email}`,
                parsed.phone && `телефон: ${parsed.phone}`, parsed.telegram && `Telegram: ${parsed.telegram}`,
                parsed.specialization_id && `специализация: ${parsed.specialization_id}`, parsed.declared_grade_id && `грейд: ${parsed.declared_grade_id}`,
                parsed.experience_years && `опыт: ${parsed.experience_years} г.`].filter(Boolean).join(' · ') || 'Контактные данные не найдены'}
            </div>
            <div className="row wrap" style={{ marginTop: 8 }}>{parsed.skills.map((s) => <span key={s.slug} className="chip">{s.name}</span>)}</div>
            <div className="row" style={{ marginTop: 12 }}><button type="button" className="btn sm" onClick={applyParsed}>Применить</button>
              <button type="button" className="btn sm ghost" onClick={() => setParsed(null)}>Отмена</button></div>
          </div>
        )}
      </div>

      <div className="split">
        <div className="stack-lg">
          <div className="card stack-lg">
            <h3>Личные данные и контакты</h3>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="profile-f1">Имя</label><input id="profile-f1" className="input" value={form.first_name} onChange={set('first_name')} /></div>
              <div className="field"><label htmlFor="profile-f2">Фамилия</label><input id="profile-f2" className="input" value={form.last_name} onChange={set('last_name')} /></div>
              <div className="field"><label htmlFor="profile-f3">Телефон</label><input id="profile-f3" className="input" value={form.phone} onChange={set('phone')} placeholder="+7 900 000-00-00" /></div>
              <div className="field"><label htmlFor="profile-f4">Telegram</label><input id="profile-f4" className="input" value={form.telegram} onChange={set('telegram')} placeholder="@username" /></div>
              <div className="field"><label htmlFor="profile-f5">Город</label><input id="profile-f5" className="input" value={form.city} onChange={set('city')} /></div>
              <div className="field"><label htmlFor="profile-f6">E-mail</label><input id="profile-f6" className="input" value={data.email} disabled /></div>
            </div>
            <p className="small muted"><ShieldCheck size={14} style={{ verticalAlign: -2 }} /> Контакты раскрываются работодателю только после того, как вы примете его приглашение или откликнетесь сами.</p>
          </div>

          <div className="card stack-lg">
            <h3>Резюме</h3>
            <div className="field"><label htmlFor="profile-f7">Заголовок</label><input id="profile-f7" className="input" value={form.headline} onChange={set('headline')} placeholder="Python backend-разработчик" /></div>
            <div className="field"><label htmlFor="profile-f8">О себе</label><textarea id="profile-f8" className="textarea" value={form.about} onChange={set('about')} placeholder="Чем занимаетесь, какие задачи интересны, чем гордитесь" /></div>
            <div className="grid grid-3">
              <div className="field"><label htmlFor="profile-f9">Опыт, лет</label><input id="profile-f9" className="input" type="number" min={0} max={50} step="any" value={form.experience_years} onChange={set('experience_years')} /></div>
              <div className="field"><label htmlFor="profile-f10">Ожидания, ₽/мес</label><input id="profile-f10" className="input" type="number" min={0} step="any" value={form.expected_salary} onChange={set('expected_salary')} /></div>
              <div className="field"><label htmlFor="profile-f11">Формат работы</label>
                <select id="profile-f11" className="select" value={form.work_format} onChange={set('work_format')}>
                  {Object.entries(WORK_FORMAT).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></div>
            </div>
            <div className="grid grid-2">
              <div className="field"><label htmlFor="profile-f12">Роли в команде</label><input id="profile-f12" className="input" value={form.team_roles} onChange={set('team_roles')} placeholder="Разработчик, Тимлид" /><span className="hint">Через запятую</span></div>
              <div className="field"><label htmlFor="profile-f13">Софт-скиллы</label><input id="profile-f13" className="input" value={form.soft_skills} onChange={set('soft_skills')} placeholder="Менторство, Коммуникабельность" /></div>
            </div>
            <div className="field"><label htmlFor="profile-f14">Образование</label><input id="profile-f14" className="input" value={form.education} onChange={set('education')} /></div>
          </div>

          <div className="card stack-lg">
            <div className="card-title" style={{ marginBottom: 0 }}><h3>Навыки и стек</h3><span className="small muted">{skills.length} навыков</span></div>
            <SkillLevelEditor value={skills} onChange={setSkills} specialization={form.specialization_id} />
            {data.skills.some((s) => s.verified) && (
              <div className="row wrap"><span className="small muted">Подтверждены тестом:</span>
                {data.skills.filter((s) => s.verified).map((s) => <span key={s.slug} className="chip verified"><ShieldCheck size={12} />{s.name} · {verifiedSkills.get(s.slug)?.competency_score}%</span>)}</div>
            )}
          </div>
        </div>

        <div className="stack-lg sticky">
          <div className="card stack">
            <h3>Опрос: специализация и грейд</h3>
            <p className="small muted">Предполагаемый грейд — гипотеза; подтверждает его тест.</p>
            <div className="field"><label htmlFor="profile-f15">Отрасль</label><input id="profile-f15" className="input" value="Информационные технологии" disabled /></div>
            <div className="field"><label htmlFor="profile-f16">Специализация</label>
              <select id="profile-f16" className="select" value={form.specialization_id} onChange={set('specialization_id')}>
                <option value="">— выберите —</option>{ref?.specializations.map((s) => <option key={s.id} value={s.id}>{s.name}</option>)}</select></div>
            <div className="field"><label htmlFor="profile-f17">Предполагаемый грейд</label>
              <select id="profile-f17" className="select" value={form.declared_grade_id} onChange={set('declared_grade_id')}>
                <option value="">— выберите —</option>{ref?.grades.map((g) => <option key={g.id} value={g.id}>{g.name}</option>)}</select></div>
          </div>
          <div className="card stack">
            <h3>Подтверждённая категория</h3>
            <CategoryBadge category={data.category} />
            <Link to="/candidate/testing" className="btn secondary sm">Перейти к тестированию</Link>
          </div>
          <div className="card stack">
            <h3>Заполненность — {data.completeness.percent}%</h3>
            <div className="bar"><i style={{ width: `${data.completeness.percent}%` }} /></div>
            {data.completeness.missing.map((m) => <div key={m.key} className="small muted">• {m.title}</div>)}
          </div>
        </div>
      </div>
    </form>
  )
}
