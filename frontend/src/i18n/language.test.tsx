import { act, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { tokenStore } from '../api/client'
import { useApi } from '../api/hooks'
import { LanguageSwitcher } from '../components/LanguageSwitcher'
import { mockFetch, renderApp } from '../test/utils'
import { useI18n } from './context'
import { langStore } from './storage'

const user = (locale: 'ru' | 'en') => ({ id: 1, email: 'a@b.c', role: 'candidate', is_email_verified: true, display_name: 'A', locale })

function Probe() {
  const { t, lang } = useI18n()
  return <><LanguageSwitcher /><p data-testid="text">{t('common.retry')}</p><p data-testid="lang">{lang}</p></>
}

describe('language switcher', () => {
  it('switches the interface, <html lang> and remembers the choice on the device', async () => {
    mockFetch()
    renderApp(<Probe />, { lang: 'ru' })
    expect(screen.getByTestId('text')).toHaveTextContent('Повторить')
    expect(screen.getByRole('button', { name: 'Русский' })).toHaveAttribute('aria-pressed', 'true')

    await userEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByTestId('text')).toHaveTextContent('Retry')
    expect(screen.getByRole('button', { name: 'English' })).toHaveAttribute('aria-pressed', 'true')
    expect(document.documentElement.lang).toBe('en')
    expect(langStore.get()).toBe('en')
    expect(screen.getByRole('group', { name: 'Interface language' })).toBeInTheDocument()
  })

  it('saves the choice to the account of a signed-in user', async () => {
    tokenStore.set('token')
    langStore.set('ru')
    const { calls } = mockFetch({ 'GET /api/auth/me': user('ru'), 'PUT /api/auth/me/locale': user('en') })
    renderApp(<Probe />)
    await waitFor(() => expect(calls.some((c) => c.url === '/api/auth/me')).toBe(true))
    await userEvent.click(screen.getByRole('button', { name: 'English' }))
    await waitFor(() => expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({ locale: 'en' }))
  })
})

describe('language precedence', () => {
  it('a device without a choice follows the browser language', () => {
    mockFetch()
    Object.defineProperty(window.navigator, 'languages', { value: ['en-US', 'en'], configurable: true })
    renderApp(<Probe />)
    expect(screen.getByTestId('lang')).toHaveTextContent('en')
    Object.defineProperty(window.navigator, 'languages', { value: ['ru-RU'], configurable: true })
  })

  it('a device without a choice adopts the account language on sign-in', async () => {
    tokenStore.set('token')
    mockFetch({ 'GET /api/auth/me': user('en') })
    renderApp(<Probe />, { lang: 'ru' })
    await waitFor(() => expect(screen.getByTestId('lang')).toHaveTextContent('en'))
    expect(langStore.get()).toBe('en')
  })

  it('a choice made on this device wins and is synced to the account', async () => {
    tokenStore.set('token')
    langStore.set('ru')
    const { calls } = mockFetch({ 'GET /api/auth/me': user('en'), 'PUT /api/auth/me/locale': user('ru') })
    renderApp(<Probe />)
    await waitFor(() => expect(calls.find((c) => c.method === 'PUT')?.body).toEqual({ locale: 'ru' }))
    expect(screen.getByTestId('lang')).toHaveTextContent('ru')
  })
})

function Loader() {
  const { data } = useApi<{ v: string }>('/reference')
  return <><LanguageSwitcher /><p data-testid="data">{data?.v}</p></>
}

describe('server-rendered texts', () => {
  it('are fetched again in the new language', async () => {
    const { calls } = mockFetch({ 'GET /api/reference': (c: { headers: Record<string, string> }) => ({ v: c.headers['Accept-Language'] }) })
    renderApp(<Loader />, { lang: 'ru' })
    await waitFor(() => expect(screen.getByTestId('data')).toHaveTextContent('ru'))
    await act(async () => { await userEvent.click(screen.getByRole('button', { name: 'English' })) })
    await waitFor(() => expect(screen.getByTestId('data')).toHaveTextContent('en'))
    expect(calls.filter((c) => c.url === '/api/reference')).toHaveLength(2)
  })
})
