import type { Lang } from './core'

const STORAGE_KEY = 'fsp_lang'

/** The language chosen on this device (null until the user picks one or an account language is adopted). */
export const langStore = {
  get(): string | null {
    try {
      return localStorage.getItem(STORAGE_KEY)
    } catch {
      return null
    }
  },
  set(lang: Lang) {
    try {
      localStorage.setItem(STORAGE_KEY, lang)
    } catch {
      /* storage unavailable: the choice lasts for this session */
    }
  },
}
