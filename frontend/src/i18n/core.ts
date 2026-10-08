// Localization core: dictionaries, plural rules, interpolation, language detection and locale-aware
// formatting. Pure functions (no React), so they are used by the API client and tested directly.
import { en } from './locales/en'
import { ru } from './locales/ru'

export type Lang = 'ru' | 'en'

export const LANGS: readonly { id: Lang; short: string; name: string }[] = [
  { id: 'ru', short: 'RU', name: 'Русский' },
  { id: 'en', short: 'EN', name: 'English' },
]
export const DEFAULT_LANG: Lang = 'ru'
/** BCP 47 tags for Intl: day-month-year order in both languages. */
export const LOCALE_TAG: Record<Lang, string> = { ru: 'ru-RU', en: 'en-GB' }

/** Plural forms by CLDR category: ru uses one / few / many (+ other for fractions), en one / other. */
export interface PluralMsg { readonly one: string; readonly few?: string; readonly many?: string; readonly other: string }
export type Msg = string | PluralMsg
export type MessageKey = keyof typeof ru
/** A dictionary must define every key of the Russian one (enforced by the type checker). */
export type Dictionary = { readonly [K in MessageKey]: Msg }
/** Parameters: numbers are formatted for the locale (pass years and ids as strings). */
export type Params = Record<string, string | number>

export const DICTS: Record<Lang, Dictionary> = { ru, en }

export const isLang = (x: unknown): x is Lang => x === 'ru' || x === 'en'

let current: Lang = DEFAULT_LANG
/** The language of the running UI; read by the API client for Accept-Language. */
export const getLang = (): Lang => current
export const setCurrentLang = (lang: Lang) => {
  current = lang
}

/** Stored choice wins; otherwise the first supported browser language; otherwise Russian. */
export function detectLanguage(stored: string | null | undefined, browser: readonly string[] = []): Lang {
  if (isLang(stored)) return stored
  for (const tag of browser) {
    const base = tag.toLowerCase().split(/[-_]/)[0]
    if (isLang(base)) return base
  }
  return DEFAULT_LANG
}

const pluralRules: Record<Lang, Intl.PluralRules> = {
  ru: new Intl.PluralRules(LOCALE_TAG.ru),
  en: new Intl.PluralRules(LOCALE_TAG.en),
}
const numberFormats: Record<Lang, Intl.NumberFormat> = {
  ru: new Intl.NumberFormat(LOCALE_TAG.ru, { maximumFractionDigits: 2 }),
  en: new Intl.NumberFormat(LOCALE_TAG.en, { maximumFractionDigits: 2 }),
}

export function pluralCategory(n: number, lang: Lang): string {
  return pluralRules[lang].select(n)
}

/** Translate a key; a missing translation falls back to Russian, a missing key to the key itself. */
export function translate(key: MessageKey, params?: Params, lang: Lang = current): string {
  let msg: Msg | undefined = DICTS[lang][key] ?? DICTS[DEFAULT_LANG][key]
  if (msg === undefined) return key
  if (typeof msg !== 'string') {
    const forms = msg as unknown as Record<string, string | undefined>
    msg = forms[pluralCategory(Number(params?.n ?? 0), lang)] ?? msg.other
  }
  if (!params) return msg
  return msg.replace(/\{(\w+)\}/g, (whole, name: string) => {
    const v = params[name]
    if (v === undefined) return whole
    return typeof v === 'number' ? numberFormats[lang].format(v) : v
  })
}

// ---------------------------------------------------------------- formatting

const DAY = 86_400_000
const NBSP = String.fromCharCode(0xa0) // keeps "180 000 ₽" on one line

export interface Formatters {
  number: (n: number) => string
  money: (n: number | null | undefined) => string
  salaryRange: (from: number, to: number) => string
  date: (iso: string | null | undefined) => string
  shortDate: (iso: string | null | undefined) => string
  time: (iso: string | null | undefined) => string
  ago: (iso: string | null | undefined, now?: number) => string
  years: (y: number) => string
  experienceFrom: (y: number) => string
  activeAgo: (days: number) => string
  /** A work period «YYYY» / «YYYY-MM» → «Feb 2023 — present» */
  period: (from: string, to?: string | null) => string
  /** Length of a work period: «1 year 8 mo» */
  tenure: (from: string, to?: string | null, now?: Date) => string
}

/** «YYYY» or «YYYY-MM» → month index (year·12 + month); a bare year means January (start) or December (end). */
const monthIndex = (p: string, end = false) => {
  const [y, m] = p.split('-').map(Number)
  return y * 12 + (m ? m - 1 : end ? 11 : 0)
}

export function createFormatters(lang: Lang): Formatters {
  const tag = LOCALE_TAG[lang]
  const whole = new Intl.NumberFormat(tag, { maximumFractionDigits: 0 })
  const longDate = new Intl.DateTimeFormat(tag, { day: 'numeric', month: 'long', year: 'numeric' })
  const short = new Intl.DateTimeFormat(tag, { day: '2-digit', month: '2-digit', year: 'numeric' })
  const time = new Intl.DateTimeFormat(tag, { hour: '2-digit', minute: '2-digit' })
  const monthYear = new Intl.DateTimeFormat(tag, { month: 'short', year: 'numeric' })
  const periodText = (p: string) => (p.length === 4 ? p : monthYear.format(new Date(Number(p.slice(0, 4)), Number(p.slice(5, 7)) - 1, 1)))
  const tr = (key: MessageKey, params?: Params) => translate(key, params, lang)
  const round1 = (y: number) => Math.round(y * 10) / 10
  return {
    number: (n) => numberFormats[lang].format(n),
    money: (n) => (n == null ? '—' : `${whole.format(n)}${NBSP}₽`),
    salaryRange: (from, to) => (from === to ? `${whole.format(from)}${NBSP}₽` : `${whole.format(from)} – ${whole.format(to)}${NBSP}₽`),
    date: (iso) => (iso ? longDate.format(new Date(iso)) : '—'),
    shortDate: (iso) => (iso ? short.format(new Date(iso)) : '—'),
    time: (iso) => (iso ? time.format(new Date(iso)) : '—'),
    ago: (iso, now = Date.now()) => {
      if (!iso) return '—'
      const days = Math.floor((now - new Date(iso).getTime()) / DAY)
      if (days <= 0) return tr('time.today')
      if (days === 1) return tr('time.yesterday')
      return tr('time.daysAgo', { n: days })
    },
    years: (y) => tr('time.years', { n: round1(y) }),
    experienceFrom: (y) => tr('time.experienceFrom', { n: round1(y) }),
    activeAgo: (days) => (days <= 0 ? tr('time.activeToday') : days === 1 ? tr('time.activeYesterday')
      : tr('time.activeDaysAgo', { n: days })),
    period: (from, to) => `${periodText(from)} — ${to ? periodText(to) : tr('exp.present')}`,
    tenure: (from, to, now = new Date()) => {
      const end = to ? monthIndex(to, true) : now.getFullYear() * 12 + now.getMonth()
      const months = Math.max(1, end - monthIndex(from) + 1)
      const y = Math.floor(months / 12)
      const m = months % 12
      return [y ? tr('time.years', { n: y }) : '', m ? tr('time.months', { n: m }) : ''].filter(Boolean).join(' ')
    },
  }
}
