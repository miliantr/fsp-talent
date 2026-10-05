/// <reference types="vite/client" />
import { describe, expect, it } from 'vitest'
import { APPLICATION_TONE, INVITATION_STATUSES, OUTCOME_TONE, WORK_FORMATS, workFormatKey } from '../lib/format'
import { DICTS, type MessageKey } from './core'

// every source file except dictionaries and tests, as raw text
const sources = import.meta.glob(['../**/*.{ts,tsx}', '!../i18n/locales/**', '!../**/*.test.{ts,tsx}', '!../api/schema.d.ts', '!../test/**'],
  { query: '?raw', import: 'default', eager: true }) as Record<string, string>

// Russian that is data, not interface text: the native name of the language and FSP sport ranks from the registry
const ALLOWED = [/name: 'Русский'/, /const RANK_ID/]

describe('no interface text outside the dictionaries', () => {
  it('scans a meaningful number of files', () => {
    expect(Object.keys(sources).length).toBeGreaterThan(30)
  })

  it('has no hardcoded Russian in components and pages', () => {
    const offenders = Object.entries(sources).flatMap(([file, text]) =>
      text.split('\n').map((line, i) => ({ file, line: i + 1, text: line.trim() }))
        .filter((l) => /[А-Яа-яЁё]/.test(l.text) && !ALLOWED.some((re) => re.test(l.text))))
    expect(offenders).toEqual([])
  })

  it('uses only keys that exist (string literals passed to t)', () => {
    const used = new Set(Object.values(sources).flatMap((text) => [...text.matchAll(/\bt\('([\w.]+)'/g)].map((m) => m[1])))
    expect([...used].filter((k) => !(k in DICTS.ru))).toEqual([])
    expect(used.size).toBeGreaterThan(300)
  })
})

describe('keys built at runtime exist in every language', () => {
  const families: Record<string, string[]> = {
    'status.invitation': INVITATION_STATUSES,
    'status.application': Object.keys(APPLICATION_TONE),
    'status.outcome': Object.keys(OUTCOME_TONE),
    'test.kind': ['initial', 'fallback', 'reconfirm', 'upgrade', 'change', 'confirm', 'blocked'],
    'cand.inv.done': ['accept', 'reject', 'report'],
    'cand.inv.modal': ['accept', 'reject', 'report'],
    'cand.fsp.rank': ['ms', 'cms', 'r1', 'r2', 'r3'],
    'skills': ['level1', 'level2', 'level3', 'level4', 'level5'],
  }
  const keys = [
    ...Object.entries(families).flatMap(([prefix, ids]) => ids.map((id) => `${prefix}.${id}`)),
    ...WORK_FORMATS.map(workFormatKey),
    ...['survey', 'test', 'category', 'shortlist', 'invitation'].flatMap((f) => [`landing.flow.${f}.title`, `landing.flow.${f}.text`]),
    ...['candidate', 'fresh', 'employer'].flatMap((d) => [`landing.demo.${d}.title`, `landing.demo.${d}.text`]),
    ...['company_name', 'industry', 'description', 'website', 'city', 'size', 'contact_name', 'contact_email', 'contact_phone', 'contact_telegram']
      .map((f) => `emp.company.field.${f}`),
  ]

  it.each(keys)('%s', (key) => {
    expect(DICTS.ru[key as MessageKey]).toBeDefined()
    expect(DICTS.en[key as MessageKey]).toBeDefined()
  })
})
