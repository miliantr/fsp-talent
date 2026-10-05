import { render } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { ToastProvider } from '../components/ui'
import type { Lang } from '../i18n/core'
import { I18nProvider } from '../i18n/context'

export interface Call { url: string; method: string; headers: Record<string, string>; body: unknown }

/** A non-2xx answer for a route of mockFetch. */
export class Reply {
  constructor(readonly status: number, readonly body: unknown) {}
}

/** Replaces fetch with a router over `routes` ("GET /api/auth/me" -> JSON, a function of the call, or a Reply)
 * and records every call. */
export function mockFetch(routes: Record<string, unknown> = {}) {
  const calls: Call[] = []
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init: RequestInit = {}) => {
    const url = String(input)
    const method = init.method ?? 'GET'
    const headers = init.headers as Record<string, string>
    calls.push({ url, method, headers, body: init.body ? JSON.parse(String(init.body)) : undefined })
    const path = url.split('?')[0]
    const key = `${method} ${path}`
    if (!(key in routes)) return new Response(JSON.stringify({ code: 'not_found', message: 'nope' }), { status: 404 })
    const value = routes[key]
    const body = typeof value === 'function' ? (value as (c: Call) => unknown)(calls[calls.length - 1]) : value
    if (body instanceof Reply) return new Response(JSON.stringify(body.body), { status: body.status })
    return new Response(JSON.stringify(body), { status: 200, headers: { 'Content-Type': 'application/json' } })
  })
  vi.stubGlobal('fetch', fetchMock)
  return { calls, fetchMock }
}

export function renderApp(ui: ReactNode, { lang, path = '/' }: { lang?: Lang; path?: string } = {}) {
  return render(
    <I18nProvider initial={lang}>
      <AuthProvider>
        <ToastProvider>
          <MemoryRouter initialEntries={[path]}>{ui}</MemoryRouter>
        </ToastProvider>
      </AuthProvider>
    </I18nProvider>,
  )
}
