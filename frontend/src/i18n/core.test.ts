import { describe, expect, it } from 'vitest'
import {
  createFormatters,
  DICTS,
  detectLanguage,
  getLang,
  pluralCategory,
  setCurrentLang,
  translate,
  type Dictionary,
  type MessageKey,
  type Msg,
} from './core'

const placeholders = (m: Msg) => {
  const texts = typeof m === 'string' ? [m] : Object.values(m).filter(Boolean) as string[]
  return new Set(texts.flatMap((s) => [...s.matchAll(/\{(\w+)\}/g)].map((x) => x[1])))
}
const CYRILLIC = /[А-Яа-яЁё]/
// English texts that legitimately contain Russian proper names (demo company)
const PROPER_NAMES = new Set<string>(['landing.demo.employer.text'])

describe('dictionaries', () => {
  const ruKeys = Object.keys(DICTS.ru).sort()
  const enKeys = Object.keys(DICTS.en).sort()

  it('define exactly the same keys', () => {
    expect(enKeys.filter((k) => !(k in DICTS.ru))).toEqual([])
    expect(ruKeys.filter((k) => !(k in DICTS.en))).toEqual([])
  })

  it('use the same placeholders in every language', () => {
    const mismatched = ruKeys.filter((k) => {
      const a = [...placeholders(DICTS.ru[k as MessageKey])].sort().join()
      const b = [...placeholders(DICTS.en[k as MessageKey])].sort().join()
      return a !== b
    })
    expect(mismatched).toEqual([])
  })

  it('give every plural message the categories of its language', () => {
    for (const [lang, dict, required] of [['ru', DICTS.ru, ['one', 'few', 'many']], ['en', DICTS.en, ['one', 'other']]] as const) {
      for (const [key, msg] of Object.entries(dict as Dictionary)) {
        if (typeof msg !== 'string') expect(Object.keys(msg), `${lang}:${key}`).toEqual(expect.arrayContaining([...required]))
      }
    }
  })

  it('have no untranslated Russian in English', () => {
    const leftovers = enKeys.filter((k) => {
      const m = DICTS.en[k as MessageKey]
      const text = typeof m === 'string' ? m : Object.values(m).join(' ')
      return CYRILLIC.test(text) && !PROPER_NAMES.has(k)
    })
    expect(leftovers).toEqual([])
  })

  it('contain no empty texts', () => {
    for (const dict of [DICTS.ru, DICTS.en]) {
      expect(Object.entries(dict).filter(([, m]) => (typeof m === 'string' ? m.trim() === '' : !m.other && !m.many))).toEqual([])
    }
  })
})

describe('translate', () => {
  it('interpolates parameters and formats numbers for the locale', () => {
    expect(translate('cand.dash.title', { name: 'Анна' }, 'ru')).toBe('Здравствуйте, Анна!')
    expect(translate('cand.dash.title', { name: 'Ann' }, 'en')).toBe('Hello, Ann!')
    expect(translate('time.years', { n: 1.5 }, 'ru')).toBe('1,5 года')
    expect(translate('time.years', { n: 1.5 }, 'en')).toBe('1.5 years')
    expect(translate('error.status', { status: '404' }, 'en')).toBe('Error 404')
  })

  it('selects plural forms by CLDR rules', () => {
    const ru = (n: number) => translate('time.daysAgo', { n }, 'ru')
    expect([1, 2, 5, 11, 21, 22, 25, 111].map(ru)).toEqual([
      '1 день назад', '2 дня назад', '5 дней назад', '11 дней назад', '21 день назад', '22 дня назад', '25 дней назад', '111 дней назад',
    ])
    expect([1, 2, 5].map((n) => translate('time.daysAgo', { n }, 'en'))).toEqual(['1 day ago', '2 days ago', '5 days ago'])
    expect(pluralCategory(1.5, 'ru')).toBe('other')
  })

  it('keeps unknown placeholders visible and returns unknown keys as is', () => {
    expect(translate('cand.dash.title', {}, 'en')).toBe('Hello, {name}!')
    expect(translate('no.such.key' as MessageKey, undefined, 'en')).toBe('no.such.key')
  })

  it('falls back to Russian when a translation is missing', () => {
    const en = DICTS.en as Record<string, Msg>
    const saved = en['common.retry']
    delete en['common.retry']
    try {
      expect(translate('common.retry', undefined, 'en')).toBe('Повторить')
    } finally {
      en['common.retry'] = saved
    }
  })

  it('uses the current language by default', () => {
    setCurrentLang('en')
    expect(getLang()).toBe('en')
    expect(translate('common.retry')).toBe('Retry')
  })
})

describe('detectLanguage', () => {
  it.each([
    [null, [], 'ru'],
    [null, ['en-GB', 'en'], 'en'],
    [null, ['de-DE', 'en-US'], 'en'],
    [null, ['de', 'fr'], 'ru'],
    ['ru', ['en-US'], 'ru'],
    ['en', ['ru-RU'], 'en'],
    ['xx', ['en_US'], 'en'],
  ] as const)('stored=%s browser=%j -> %s', (stored, browser, expected) => {
    expect(detectLanguage(stored, browser)).toBe(expected)
  })
})

describe('formatters', () => {
  const ru = createFormatters('ru')
  const en = createFormatters('en')
  const ws = (s: string) => s.replace(/\s/g, ' ')  // Intl uses (narrow) no-break spaces

  it('format money and salary ranges', () => {
    expect(ws(ru.money(180000))).toBe('180 000 ₽')
    expect(ws(en.money(180000))).toBe('180,000 ₽')
    expect(ws(en.salaryRange(180000, 250000))).toBe('180,000 – 250,000 ₽')
    expect(ws(ru.salaryRange(200000, 200000))).toBe('200 000 ₽')
    expect(ru.money(null)).toBe('—')
  })

  it('format dates day-month-year in both languages', () => {
    expect(en.date('2026-10-05T12:00:00Z')).toBe('5 October 2026')
    expect(ru.date('2026-10-05T12:00:00Z')).toMatch(/^5 октября 2026/)
    expect(en.shortDate('2026-10-05T12:00:00Z')).toBe('05/10/2026')
    expect(ru.shortDate('2026-10-05T12:00:00Z')).toBe('05.10.2026')
  })

  it('format relative days and durations', () => {
    const now = Date.parse('2026-10-05T12:00:00Z')
    expect(en.ago('2026-10-05T08:00:00Z', now)).toBe('today')
    expect(ru.ago('2026-10-04T08:00:00Z', now)).toBe('вчера')
    expect(ru.ago('2026-10-02T08:00:00Z', now)).toBe('3 дня назад')
    expect(en.ago(null)).toBe('—')
    expect([1, 3, 5].map(ru.years)).toEqual(['1 год', '3 года', '5 лет'])
    expect(en.experienceFrom(2)).toBe('2+ years')
    expect(ru.experienceFrom(1)).toBe('от 1 года')
    expect(en.activeAgo(0)).toBe('active today')
  })
})
