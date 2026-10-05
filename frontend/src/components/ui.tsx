import { AlertCircle, Check, ChevronRight, Minus, Search, ShieldCheck, Trophy, X } from 'lucide-react'
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import type {
  Category,
  CompetencyScore,
  ComponentOut,
  FSPAchievementView,
  FSPSummaryView,
  ReasonOut,
  SkillMatch,
} from '../api/types'
import type { MessageKey } from '../i18n/core'
import { useI18n } from '../i18n/context'
import { APPLICATION_TONE, COMPONENT_COLORS, INVITATION_TONE, OUTCOME_TONE } from '../lib/format'

export function Loading({ label }: { label?: string }) {
  return (
    <div className="loading">
      <div className="stack" style={{ alignItems: 'center' }}>
        <div className="spinner" />
        {label && <span className="muted small">{label}</span>}
      </div>
    </div>
  )
}

export function ErrorBox({ error, onRetry }: { error: string | null; onRetry?: () => void }) {
  const { t } = useI18n()
  if (!error) return null
  return (
    <div className="alert error" role="alert">
      <AlertCircle size={18} />
      <div style={{ flex: 1 }}>{error}</div>
      {onRetry && <button className="btn sm ghost" onClick={onRetry}>{t('common.retry')}</button>}
    </div>
  )
}

export function Empty({ icon, title, text, action }: { icon?: ReactNode; title: string; text?: ReactNode; action?: ReactNode }) {
  return (
    <div className="empty">
      <div className="icon">{icon ?? <Search size={26} />}</div>
      <h3>{title}</h3>
      {text && <p className="small" style={{ maxWidth: 460, margin: '0 auto' }}>{text}</p>}
      {action && <div style={{ marginTop: 16 }}>{action}</div>}
    </div>
  )
}

export function Badge({ tone = 'muted', children }: { tone?: string; children: ReactNode }) {
  return <span className={`badge ${tone}`}>{children}</span>
}

function StatusBadge({ kind, status, tones }: { kind: string; status: string; tones: Record<string, string> }) {
  const { t } = useI18n()
  const label = t(`status.${kind}.${status}` as MessageKey)
  return <Badge tone={tones[status] ?? 'muted'}>{label.startsWith('status.') ? status : label}</Badge>
}

export const InvitationStatusBadge = ({ status }: { status: string }) =>
  <StatusBadge kind="invitation" status={status} tones={INVITATION_TONE} />

export const ApplicationStatusBadge = ({ status }: { status: string }) =>
  <StatusBadge kind="application" status={status} tones={APPLICATION_TONE} />

export const OutcomeBadge = ({ outcome }: { outcome: string }) =>
  <StatusBadge kind="outcome" status={outcome} tones={OUTCOME_TONE} />

export function CategoryBadge({ category, size }: { category: Category | null | undefined; size?: 'lg' }) {
  const { t } = useI18n()
  if (!category) {
    return <span className={`category none ${size ?? ''}`}><span className="ok"><Minus size={14} /></span>{t('category.none')}</span>
  }
  return (
    <span className={`category ${size ?? ''}`} title={t('category.verifiedTitle')}>
      <span className="ok"><ShieldCheck size={size ? 18 : 14} /></span>
      {category.label}
    </span>
  )
}

export function ScoreRing({ value, size = 76, label, color }: { value: number; size?: number; label?: string; color?: string }) {
  const r = (size - 10) / 2
  const c = 2 * Math.PI * r
  const v = Math.max(0, Math.min(100, value))
  const stroke = color ?? (v >= 75 ? 'var(--success)' : v >= 55 ? 'var(--primary)' : 'var(--warning)')
  const text = `${Math.round(v)}${label ? '' : '%'}`
  return (
    <div className="ring" style={{ width: size, height: size }} aria-label={`${v}%`}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} stroke="var(--surface-3)" strokeWidth="8" fill="none" />
        <circle cx={size / 2} cy={size / 2} r={r} stroke={stroke} strokeWidth="8" fill="none" strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - v / 100)} style={{ transition: 'stroke-dashoffset .6s ease' }} />
      </svg>
      <div className="val">
        <b style={{ fontSize: size * (text.length >= 4 ? 0.2 : text.length === 3 ? 0.24 : 0.28) }}>{text}</b>
        {label && <span>{label}</span>}
      </div>
    </div>
  )
}

export function Bar({ value, tone }: { value: number; tone?: 'success' | 'warning' }) {
  return <div className={`bar ${tone ?? ''}`}><i style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
}

/** 0–100 scaled score with the grade bands (25 Junior / 50 Middle / 75 Senior). */
export function ScoreScale({ score }: { score: number }) {
  const { t } = useI18n()
  return (
    <div className="scale" aria-label={t('scale.aria', { score })}>
      <div className="marker" style={{ left: `${Math.max(2, Math.min(98, score))}%` }}><b>{score}</b><i /></div>
      <div className="track"><i /><i /><i /><i /></div>
      <div className="ticks"><span>&lt; 25</span><span>Junior 25+</span><span>Middle 50+</span><span>Senior 75+</span></div>
    </div>
  )
}

export function CompetencyBars({ items }: { items: CompetencyScore[] }) {
  const { t } = useI18n()
  if (!items.length) return <p className="muted small">{t('competencies.empty')}</p>
  return (
    <div className="stack">
      {items.map((c) => (
        <div key={c.id}>
          <div className="row between small"><span>{c.name}</span><b>{c.score}%</b></div>
          <Bar value={c.score} tone={c.score >= 70 ? 'success' : c.score < 45 ? 'warning' : undefined} />
        </div>
      ))}
    </div>
  )
}

const REASON_ICON = { positive: <Check size={14} />, neutral: <ChevronRight size={14} />, negative: <X size={14} /> }

export function Reasons({ reasons, limit }: { reasons: ReasonOut[]; limit?: number }) {
  const list = limit ? reasons.slice(0, limit) : reasons
  return (
    <div>
      {list.map((r, i) => (
        <div key={i} className={`reason ${r.kind}`}>
          <span className="ic">{REASON_ICON[r.kind]}</span>
          <span>{r.text}</span>
        </div>
      ))}
    </div>
  )
}


/** Contribution of each component to the final score (points out of 100). */
export function MatchBreakdown({ components, mustGate, detailed }: { components: ComponentOut[]; mustGate?: number; detailed?: boolean }) {
  const { t, fmt } = useI18n()
  const avail = components.filter((c) => c.available)
  const pts = (x: number) => fmt.number(Math.round(x * 10) / 10)
  return (
    <div className="stack">
      <div className="stacked" aria-hidden>
        {avail.map((c) => (
          <i key={c.key} title={`${c.label}: ${pts(c.contribution)}`}
            style={{ width: `${c.contribution}%`, background: COMPONENT_COLORS[c.key] }} />
        ))}
      </div>
      <div className="legend">
        {avail.map((c) => (
          <span key={c.key}><i style={{ background: COMPONENT_COLORS[c.key] }} />{c.label} {pts(c.contribution)}</span>
        ))}
      </div>
      {detailed && (
        <div className="table-wrap" style={{ marginTop: 6 }}>
          <table className="table">
            <thead><tr><th>{t('breakdown.factor')}</th><th>{t('breakdown.score')}</th><th>{t('breakdown.weight')}</th>
              <th>{t('breakdown.contribution')}</th><th>{t('breakdown.details')}</th></tr></thead>
            <tbody>
              {components.map((c) => (
                <tr key={c.key} style={{ opacity: c.available ? 1 : 0.5 }}>
                  <td><span className="row"><i style={{ width: 10, height: 10, borderRadius: 3, background: COMPONENT_COLORS[c.key], display: 'inline-block' }} />{c.label}</span></td>
                  <td style={{ width: 140 }}>{c.available ? <div className="row"><div style={{ flex: 1 }}><Bar value={c.value * 100} /></div><span className="tiny">{Math.round(c.value * 100)}</span></div> : <span className="muted small">{t('breakdown.noData')}</span>}</td>
                  <td className="small">{c.available ? `${Math.round(c.weight * 100)}%` : '—'}</td>
                  <td className="bold">{c.available ? pts(c.contribution) : '—'}</td>
                  <td className="small muted">{c.detail}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {mustGate !== undefined && mustGate < 0.999 && (
            <p className="small muted" style={{ marginTop: 8 }}>
              {t('breakdown.mustGate')} <b>×{fmt.number(Math.round(mustGate * 100) / 100)}</b> {t('breakdown.mustGateNote')}
            </p>
          )}
        </div>
      )}
    </div>
  )
}

export function SkillMatchChips({ items }: { items: SkillMatch[] }) {
  const { t } = useI18n()
  return (
    <div className="row wrap">
      {items.map((s) => (
        <span key={s.skill} className={`chip ${s.status === 'missing' ? 'missing' : s.status === 'related' ? 'related' : s.verified ? 'verified' : ''}`}
          title={s.status === 'related' ? t('skills.related', { via: s.via ?? '' }) : s.verified ? t('skills.verified')
            : s.importance === 'must' ? t('skills.must') : t('skills.nice')}>
          {s.status === 'exact' && s.verified && <ShieldCheck size={13} />}
          {s.name}{s.status === 'related' && <span className="tiny"> ≈ {s.via}</span>}
          {s.importance === 'nice' && <span className="tiny muted">{t('skills.niceShort')}</span>}
        </span>
      ))}
    </div>
  )
}

export function FspSummary({ fsp, compact }: { fsp: FSPSummaryView; compact?: boolean }) {
  const { t } = useI18n()
  if (!fsp.available) {
    return <span className="badge muted" title={t('fsp.noHistoryTitle')}>{t('fsp.noHistory')}</span>
  }
  return (
    <span className="badge accent" title={fsp.highlights.join('\n')}>
      <Trophy size={13} />
      {t('fsp.achievements', { n: fsp.count })}
      {!compact && fsp.prizes > 0 && ` · ${t('fsp.prizes', { n: fsp.prizes })}`}
    </span>
  )
}

export function Medal({ place }: { place: number | null | undefined }) {
  const cls = place === 1 ? 'p1' : place === 2 ? 'p2' : place === 3 ? 'p3' : 'pn'
  return <span className={`medal ${cls}`}>{place ?? '—'}</span>
}

export function AchievementList({ items }: { items: FSPAchievementView[] }) {
  const { t, fmt } = useI18n()
  return (
    <div className="stack">
      {items.map((a) => (
        <div key={a.id} className="row" style={{ alignItems: 'flex-start', gap: 12, padding: '10px 0', borderBottom: '1px solid var(--border)' }}>
          <Medal place={a.place} />
          <div style={{ flex: 1 }}>
            <div className="bold">{a.event_name}</div>
            <div className="small muted">
              {a.discipline} · {a.level_name} · {fmt.date(a.date)}
              {a.participants_total ? ` · ${a.place ? t('fsp.placeOf', { place: a.place, total: a.participants_total })
                : t('fsp.participants', { n: a.participants_total })}` : ''}
            </div>
            <div className="row wrap" style={{ marginTop: 6 }}>
              {a.team_name && <Badge tone="outline">{t('fsp.team', { team: a.team_name })}</Badge>}
              {a.role && <Badge tone="violet">{t('fsp.role', { role: a.role })}</Badge>}
              {a.score != null && <Badge tone="outline">{t('fsp.points', { n: a.score })}</Badge>}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export function Modal({ title, onClose, children, wide }: { title: ReactNode; onClose: () => void; children: ReactNode; wide?: boolean }) {
  const { t } = useI18n()
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="modal-back" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" style={wide ? { maxWidth: 860 } : undefined}>
        <div className="modal-head"><h2>{title}</h2><button className="icon-btn" onClick={onClose} aria-label={t('common.close')}><X size={20} /></button></div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  )
}

export function Switch({ checked, onChange, label, hint }: { checked: boolean; onChange: (v: boolean) => void; label: string; hint?: string }) {
  return (
    <label className="row between" style={{ cursor: 'pointer', gap: 16, padding: '10px 0' }}>
      <span><span className="bold">{label}</span>{hint && <span className="small muted" style={{ display: 'block' }}>{hint}</span>}</span>
      <span className="switch"><input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} /><span /></span>
    </label>
  )
}

export function Tabs<T extends string>({ value, onChange, items }: { value: T; onChange: (v: T) => void; items: { id: T; label: ReactNode }[] }) {
  return (
    <div className="tabs" role="tablist">
      {items.map((t) => (
        <button key={t.id} role="tab" aria-selected={value === t.id} className={`tab ${value === t.id ? 'active' : ''}`} onClick={() => onChange(t.id)}>{t.label}</button>
      ))}
    </div>
  )
}

export function Avatar({ name, size }: { name: string; size?: 'lg' }) {
  const initials = name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase()
  return <span className={`avatar ${size ?? ''}`}>{initials || '?'}</span>
}

/** Renders question text with `inline code` and ```fenced``` blocks. */
export function RichText({ text }: { text: string }) {
  const parts = text.split(/```(?:\w+)?\n?([\s\S]*?)```/g)
  return (
    <div className="q-text">
      {parts.map((p, i) =>
        i % 2 === 1 ? <pre key={i}><code>{p.replace(/\n$/, '')}</code></pre> : (
          <span key={i}>{p.split(/`([^`]+)`/g).map((s, j) => (j % 2 ? <code key={j}>{s}</code> : s))}</span>
        ))}
    </div>
  )
}

// ---------------------------------------------------------------- toast
const ToastCtx = createContext<(msg: string) => void>(() => {})

export function ToastProvider({ children }: { children: ReactNode }) {
  const [msg, setMsg] = useState<string | null>(null)
  const show = useCallback((m: string) => {
    setMsg(m)
    window.setTimeout(() => setMsg(null), 3200)
  }, [])
  return (
    <ToastCtx.Provider value={show}>
      {children}
      {msg && <div className="toast" role="status"><Check size={18} />{msg}</div>}
    </ToastCtx.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => useContext(ToastCtx)
