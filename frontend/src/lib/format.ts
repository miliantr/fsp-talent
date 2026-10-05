// Presentation helpers only (formatting and display labels). No business rules here.

export const rub = (n: number | null | undefined) =>
  n == null ? '—' : `${n.toLocaleString('ru-RU').replace(/,/g, ' ')} ₽`

export const salaryRange = (from: number, to: number) =>
  from === to ? rub(from) : `${from.toLocaleString('ru-RU')} – ${to.toLocaleString('ru-RU')} ₽`

export const date = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' }) : '—'

export const shortDate = (iso: string | null | undefined) =>
  iso ? new Date(iso).toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }) : '—'

export const ago = (iso: string | null | undefined) => {
  if (!iso) return '—'
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (days <= 0) return 'сегодня'
  if (days === 1) return 'вчера'
  return `${days} ${plural(days, 'день', 'дня', 'дней')} назад`
}

export function plural(n: number, one: string, few: string, many: string) {
  const m10 = n % 10
  const m100 = n % 100
  if (m10 === 1 && m100 !== 11) return one
  if (m10 >= 2 && m10 <= 4 && (m100 < 12 || m100 > 14)) return few
  return many
}

export const years = (y: number) => {
  const n = Math.round(y * 10) / 10
  if (!Number.isInteger(n)) return `${n.toString().replace('.', ',')} года`
  return `${n} ${plural(n, 'год', 'года', 'лет')}`
}

/** "опыт от 2 лет", "от 1 года", "от 1,5 года" */
export const experienceFrom = (y: number) => {
  const n = Math.round(y * 10) / 10
  const s = n.toString().replace('.', ',')
  return `от ${s} ${n === 1 || !Number.isInteger(n) ? 'года' : 'лет'}`
}

export const activeAgo = (days: number) =>
  days <= 0 ? 'активен сегодня' : days === 1 ? 'активен вчера' : `активен ${days} ${plural(days, 'день', 'дня', 'дней')} назад`

export const WORK_FORMAT: Record<string, string> = {
  remote: 'Удалённо', office: 'Офис', hybrid: 'Гибрид', any: 'Любой формат',
}

export const INVITATION_STATUS: Record<string, { label: string; tone: string }> = {
  sent: { label: 'Отправлено', tone: 'info' },
  viewed: { label: 'Просмотрено', tone: 'violet' },
  accepted: { label: 'Принято', tone: 'success' },
  rejected: { label: 'Отклонено', tone: 'danger' },
  expired: { label: 'Истекло', tone: 'muted' },
  withdrawn: { label: 'Отозвано', tone: 'muted' },
}

export const APPLICATION_STATUS: Record<string, { label: string; tone: string }> = {
  sent: { label: 'Отправлен', tone: 'info' },
  viewed: { label: 'Просмотрен', tone: 'violet' },
  accepted: { label: 'Приглашён', tone: 'success' },
  rejected: { label: 'Отказ', tone: 'danger' },
}

export const OUTCOME: Record<string, { label: string; tone: string }> = {
  passed: { label: 'Грейд подтверждён', tone: 'success' },
  passed_upgrade: { label: 'Подтверждён с запасом', tone: 'success' },
  not_passed: { label: 'Не подтверждён', tone: 'warning' },
  needs_confirmation: { label: 'Нужно подтверждение', tone: 'warning' },
}

export const FSP_LEVEL_ORDER = ['international', 'all_russian', 'interregional', 'regional']

export const COMPONENT_COLORS: Record<string, string> = {
  skills: '#6b21d6', test: '#2563eb', grade: '#0f9d63', specialization: '#14b8a6', fsp: '#d63aa7',
  freshness: '#f59e0b', salary: '#64748b', experience: '#a78bfa', format: '#94a3b8',
}
