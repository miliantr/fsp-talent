import { Plus, X } from 'lucide-react'
import { useMemo, useState } from 'react'
import type { MessageKey } from '../i18n/core'
import { useI18n } from '../i18n/context'
import { useReference } from '../lib/reference'

function useSkillSearch(exclude: string[], specialization?: string | null) {
  const { ref } = useReference()
  const [q, setQ] = useState('')
  const options = useMemo(() => {
    const all = ref?.skills ?? []
    const ql = q.trim().toLowerCase()
    return all
      .filter((s) => !exclude.includes(s.slug))
      .filter((s) => !ql || s.name.toLowerCase().includes(ql) || s.slug.includes(ql))
      .sort((a, b) => {
        const sa = specialization && a.specializations.includes(specialization) ? 0 : 1
        const sb = specialization && b.specializations.includes(specialization) ? 0 : 1
        return sa - sb || a.name.localeCompare(b.name)
      })
      .slice(0, ql ? 12 : 16)
  }, [ref, q, exclude, specialization])
  return { q, setQ, options }
}

/** Chips selector for employer requirements (must / nice skills). */
export function SkillSelect({ value, onChange, specialization, placeholder }: {
  value: string[]; onChange: (v: string[]) => void; specialization?: string | null; placeholder?: string
}) {
  const { skillName } = useReference()
  const { t } = useI18n()
  const { q, setQ, options } = useSkillSearch(value, specialization)
  const [open, setOpen] = useState(false)
  return (
    <div className="stack" style={{ position: 'relative' }}>
      <div className="row wrap">
        {value.map((s) => (
          <span key={s} className="chip on">{skillName(s)}
            <button type="button" aria-label={t('skills.remove', { name: skillName(s) })} onClick={() => onChange(value.filter((x) => x !== s))}><X size={13} /></button></span>
        ))}
      </div>
      <input className="input" placeholder={placeholder ?? t('skills.addPlaceholder')} value={q} onChange={(e) => { setQ(e.target.value); setOpen(true) }}
        onFocus={() => setOpen(true)} onBlur={() => window.setTimeout(() => setOpen(false), 150)} />
      {open && options.length > 0 && (
        <div className="row wrap card" style={{ position: 'absolute', top: '100%', left: 0, right: 0, zIndex: 10, marginTop: 4, padding: 10, boxShadow: 'var(--shadow-lg)' }}>
          {options.map((o) => (
            <button type="button" key={o.slug} className="chip selectable" onMouseDown={(e) => e.preventDefault()}
              onClick={() => { onChange([...value, o.slug]); setQ('') }}><Plus size={12} />{o.name}</button>
          ))}
        </div>
      )}
    </div>
  )
}

export interface SkillLevel { slug: string; level: number; years: number }

const levelKey = (level: number) => `skills.level${level}` as MessageKey

/** Candidate skills with self-assessed level and years. */
export function SkillLevelEditor({ value, onChange, specialization }: {
  value: SkillLevel[]; onChange: (v: SkillLevel[]) => void; specialization?: string | null
}) {
  const { skillName } = useReference()
  const { t } = useI18n()
  const { q, setQ, options } = useSkillSearch(value.map((v) => v.slug), specialization)
  const update = (slug: string, patch: Partial<SkillLevel>) => onChange(value.map((v) => (v.slug === slug ? { ...v, ...patch } : v)))
  return (
    <div className="stack">
      {value.length === 0 && <p className="small muted">{t('skills.empty')}</p>}
      {value.map((s) => (
        <div key={s.slug} className="row wrap" style={{ gap: 12, padding: '8px 12px', border: '1px solid var(--border)', borderRadius: 12 }}>
          <b style={{ minWidth: 140 }}>{skillName(s.slug)}</b>
          <input type="range" min={1} max={5} value={s.level} onChange={(e) => update(s.slug, { level: Number(e.target.value) })}
            aria-label={t('skills.levelAria', { name: skillName(s.slug) })} style={{ accentColor: 'var(--primary)' }} />
          <span className="small" style={{ minWidth: 92 }}>{t(levelKey(s.level))}</span>
          <input className="input" style={{ width: 90, padding: '6px 10px' }} type="number" min={0} max={50} step="any" value={s.years}
            onChange={(e) => update(s.slug, { years: Number(e.target.value) })} aria-label={t('skills.yearsAria')} />
          <span className="small muted">{t('skills.yearsUnit')}</span>
          <button type="button" className="icon-btn right" onClick={() => onChange(value.filter((v) => v.slug !== s.slug))}
            aria-label={t('skills.delete')}><X size={16} /></button>
        </div>
      ))}
      <input className="input" placeholder={t('skills.searchPlaceholder')} value={q} onChange={(e) => setQ(e.target.value)} />
      <div className="row wrap">
        {options.slice(0, 14).map((o) => (
          <button type="button" key={o.slug} className="chip selectable" onClick={() => { onChange([...value, { slug: o.slug, level: 3, years: 1 }]); setQ('') }}>
            <Plus size={12} />{o.name}</button>
        ))}
      </div>
    </div>
  )
}
