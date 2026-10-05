import { useAuth } from '../auth/AuthContext'
import { LANGS } from '../i18n/core'
import { useI18n } from '../i18n/context'

/** RU / EN toggle. A signed-in user's choice is also saved to the account. */
export function LanguageSwitcher({ tone }: { tone?: 'light' }) {
  const { lang, t } = useI18n()
  const { changeLanguage } = useAuth()
  return (
    <div className={`lang-switch ${tone ?? ''}`} role="group" aria-label={t('lang.label')}>
      {LANGS.map((l) => (
        <button key={l.id} type="button" lang={l.id} title={l.name} aria-label={l.name} aria-pressed={lang === l.id}
          className={lang === l.id ? 'on' : ''} onClick={() => changeLanguage(l.id)}>{l.short}</button>
      ))}
    </div>
  )
}
