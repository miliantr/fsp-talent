import { Briefcase, Plus, Trash2 } from 'lucide-react'
import type { ExperienceItem } from '../api/types'
import { useI18n } from '../i18n/context'
import { toMonth } from '../lib/format'

/** Places of work, the most recent first: position, company, period and its length. */
export function ExperienceList({ items }: { items: ExperienceItem[] }) {
  const { t, fmt } = useI18n()
  if (items.length === 0) return <p className="small muted" style={{ margin: 0 }}>{t('exp.empty')}</p>
  return (
    <div className="stack" style={{ gap: 12 }}>
      {items.map((e, i) => (
        <div key={`${e.company}-${e.period_from}-${i}`} className="row" style={{ alignItems: 'flex-start', gap: 12 }}>
          <span className="exp-icon"><Briefcase size={16} /></span>
          <div style={{ flex: 1 }}>
            <div className="bold">{e.position}</div>
            <div className="small">{e.company}</div>
            <div className="tiny muted">{fmt.period(e.period_from, e.period_to)} · {fmt.tenure(e.period_from, e.period_to)}</div>
            {e.description && <div className="small" style={{ marginTop: 4 }}>{e.description}</div>}
          </div>
        </div>
      ))}
    </div>
  )
}

/** Editable list of places of work (the profile form). */
export function ExperienceEditor({ value, onChange }: { value: ExperienceItem[]; onChange: (v: ExperienceItem[]) => void }) {
  const { t } = useI18n()
  const patch = (i: number, p: Partial<ExperienceItem>) => onChange(value.map((e, k) => (k === i ? { ...e, ...p } : e)))
  return (
    <div className="stack">
      {value.map((e, i) => (
        <div key={i} className="card flat stack" style={{ gap: 10 }}>
          <div className="grid grid-2">
            <div className="field"><label htmlFor={`exp-company-${i}`}>{t('exp.company')}</label>
              <input id={`exp-company-${i}`} className="input" value={e.company} onChange={(x) => patch(i, { company: x.target.value })} /></div>
            <div className="field"><label htmlFor={`exp-position-${i}`}>{t('exp.position')}</label>
              <input id={`exp-position-${i}`} className="input" value={e.position} onChange={(x) => patch(i, { position: x.target.value })} /></div>
            <div className="field"><label htmlFor={`exp-from-${i}`}>{t('exp.from')}</label>
              <input id={`exp-from-${i}`} className="input" type="month" value={toMonth(e.period_from)} onChange={(x) => patch(i, { period_from: x.target.value })} /></div>
            <div className="field"><label htmlFor={`exp-to-${i}`}>{t('exp.to')}</label>
              <input id={`exp-to-${i}`} className="input" type="month" disabled={!e.period_to} value={toMonth(e.period_to)}
                onChange={(x) => patch(i, { period_to: x.target.value || null })} />
              <label className="check small"><input type="checkbox" checked={!e.period_to}
                onChange={(x) => patch(i, { period_to: x.target.checked ? null : (e.period_from || '') })} />{t('exp.current')}</label></div>
          </div>
          <div className="field"><label htmlFor={`exp-desc-${i}`}>{t('exp.description')}</label>
            <textarea id={`exp-desc-${i}`} className="textarea" style={{ minHeight: 60 }} value={e.description ?? ''} onChange={(x) => patch(i, { description: x.target.value })} /></div>
          <div className="row"><button type="button" className="btn ghost sm" onClick={() => onChange(value.filter((_, k) => k !== i))}>
            <Trash2 size={14} />{t('exp.remove')}</button></div>
        </div>
      ))}
      <div className="row"><button type="button" className="btn secondary sm"
        onClick={() => onChange([...value, { company: '', position: '', period_from: '', period_to: null, description: '' }])}>
        <Plus size={14} />{t('exp.add')}</button></div>
      <p className="tiny muted" style={{ margin: 0 }}>{t('exp.hint')}</p>
    </div>
  )
}
