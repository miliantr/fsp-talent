// Presentation constants only. Texts and locale-aware formatting live in src/i18n
// (useI18n(): t for labels, fmt for numbers, money, dates and durations).
import type { MessageKey } from '../i18n/core'

export const WORK_FORMATS = ['remote', 'office', 'hybrid', 'any'] as const
export const workFormatKey = (format: string) => `format.${format}` as MessageKey

export const INVITATION_TONE: Record<string, string> = {
  sent: 'info', viewed: 'violet', accepted: 'success', rejected: 'danger', expired: 'muted', withdrawn: 'muted',
}
export const APPLICATION_TONE: Record<string, string> = {
  sent: 'info', viewed: 'violet', accepted: 'success', rejected: 'danger',
}
export const OUTCOME_TONE: Record<string, string> = {
  passed: 'success', passed_upgrade: 'success', not_passed: 'warning', needs_confirmation: 'warning',
}
export const INVITATION_STATUSES = Object.keys(INVITATION_TONE)

export const FSP_LEVEL_ORDER = ['international', 'all_russian', 'interregional', 'regional']

export const COMPONENT_COLORS: Record<string, string> = {
  skills: '#6b21d6', test: '#2563eb', grade: '#0f9d63', specialization: '#14b8a6', fsp: '#d63aa7',
  freshness: '#f59e0b', salary: '#64748b', experience: '#a78bfa', format: '#94a3b8',
}
