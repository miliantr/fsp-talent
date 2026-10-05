import { screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it } from 'vitest'
import { mockFetch, renderApp, Reply, type Call } from '../test/utils'
import Login from './auth/Login'
import Register from './auth/Register'
import Landing from './Landing'

describe('landing page', () => {
  it.each([
    ['ru', 'Как это работает', 'Я ищу работу', 'Войти в демо'],
    ['en', 'How it works', 'I am looking for a job', 'Sign in to the demo'],
  ] as const)('renders in %s', (lang, heading, cta, demo) => {
    mockFetch()
    renderApp(<Landing />, { lang })
    expect(screen.getByRole('heading', { name: heading })).toBeInTheDocument()
    expect(screen.getByRole('link', { name: cta })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: demo })).toHaveLength(3)
  })

  it('switches language in place', async () => {
    mockFetch()
    renderApp(<Landing />, { lang: 'ru' })
    await userEvent.click(screen.getByRole('button', { name: 'English' }))
    expect(screen.getByRole('heading', { name: 'How it works' })).toBeInTheDocument()
    expect(screen.queryByText('Как это работает')).not.toBeInTheDocument()
  })
})

describe('auth forms', () => {
  it('label fields in the chosen language (accessible names)', () => {
    mockFetch()
    renderApp(<Login />, { lang: 'en' })
    expect(screen.getByLabelText('E-mail')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeInTheDocument()
  })

  it('show the server error message, requested in the chosen language', async () => {
    // the backend renders the message in the Accept-Language of the request
    const { calls } = mockFetch({
      'POST /api/auth/login': (c: Call) => new Reply(401, {
        code: 'invalid_credentials',
        message: c.headers['Accept-Language'] === 'en' ? 'Invalid e-mail or password' : 'Неверный e-mail или пароль',
      }),
    })
    renderApp(<Login />, { lang: 'en' })
    await userEvent.type(screen.getByLabelText('E-mail'), 'x@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign in' }))
    expect(await screen.findByText('Invalid e-mail or password')).toBeInTheDocument()
    expect(calls[0].body).toEqual({ email: 'x@example.com', password: 'secret123' })
  })

  it('validate consent on registration in the chosen language', async () => {
    mockFetch()
    renderApp(<Register />, { lang: 'en' })
    await userEvent.type(screen.getByLabelText('First name'), 'Ann')
    await userEvent.type(screen.getByLabelText('Last name'), 'Lee')
    await userEvent.type(screen.getByLabelText('E-mail'), 'ann@example.com')
    await userEvent.type(screen.getByLabelText('Password'), 'secret123')
    await userEvent.click(screen.getByRole('button', { name: 'Sign up' }))
    expect(await screen.findByText('Consent to personal data processing is required')).toBeInTheDocument()
  })
})
