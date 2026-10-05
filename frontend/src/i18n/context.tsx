import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  createFormatters,
  detectLanguage,
  setCurrentLang,
  translate,
  type Formatters,
  type Lang,
  type MessageKey,
  type Params,
} from './core'
import { langStore } from './storage'

export interface I18nValue {
  lang: Lang
  setLang: (lang: Lang) => void
  t: (key: MessageKey, params?: Params) => string
  fmt: Formatters
}

const I18nContext = createContext<I18nValue | null>(null)

function browserLanguages(): readonly string[] {
  if (typeof navigator === 'undefined') return []
  return navigator.languages?.length ? navigator.languages : [navigator.language]
}

export function I18nProvider({ children, initial }: { children: ReactNode; initial?: Lang }) {
  const [lang, setLangState] = useState<Lang>(() => {
    const l = initial ?? detectLanguage(langStore.get(), browserLanguages())
    setCurrentLang(l) // before the first render, so the first requests already carry the language
    return l
  })

  const setLang = useCallback((l: Lang) => {
    setCurrentLang(l)
    langStore.set(l)
    setLangState(l)
  }, [])

  useEffect(() => {
    document.documentElement.lang = lang
  }, [lang])

  const value = useMemo<I18nValue>(() => ({
    lang,
    setLang,
    t: (key, params) => translate(key, params, lang),
    fmt: createFormatters(lang),
  }), [lang, setLang])

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>
}

// eslint-disable-next-line react-refresh/only-export-components
export function useI18n(): I18nValue {
  const ctx = useContext(I18nContext)
  if (!ctx) throw new Error('useI18n outside I18nProvider')
  return ctx
}
