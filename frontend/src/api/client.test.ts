import { describe, expect, it, vi } from 'vitest'
import { setCurrentLang } from '../i18n/core'
import { mockFetch } from '../test/utils'
import { api, ApiError, errorMessage, tokenStore } from './client'

describe('api client', () => {
  it('sends the UI language with every request', async () => {
    const { calls } = mockFetch({ 'GET /api/reference': {} })
    await api('/reference')
    setCurrentLang('en')
    await api('/reference')
    expect(calls.map((c) => c.headers['Accept-Language'])).toEqual(['ru', 'en'])
  })

  it('adds the bearer token and JSON body', async () => {
    tokenStore.set('abc')
    const { calls } = mockFetch({ 'POST /api/x': { ok: true } })
    await api('/x', { method: 'POST', body: { a: 1 }, query: { q: 'py', tags: ['a', 'b'], empty: '' } })
    expect(calls[0].url).toBe('/api/x?q=py&tags=a&tags=b')
    expect(calls[0].headers).toMatchObject({ Authorization: 'Bearer abc', 'Content-Type': 'application/json' })
    expect(calls[0].body).toEqual({ a: 1 })
  })

  it('surfaces the server message (already in the request language)', async () => {
    mockFetch()
    const err = await api('/missing').catch((e) => e)
    expect(err).toBeInstanceOf(ApiError)
    expect(err).toMatchObject({ status: 404, code: 'not_found', message: 'nope' })
  })

  it('localizes client-side errors', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline') }))
    setCurrentLang('en')
    expect(errorMessage(await api('/x').catch((e) => e))).toBe('The server is unavailable. Check that the backend is running.')
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 502 })))
    expect(errorMessage(await api('/x').catch((e) => e))).toBe('Error 502')
    expect(errorMessage('weird')).toBe('Something went wrong')
    setCurrentLang('ru')
    expect(errorMessage(42)).toBe('Что-то пошло не так')
  })

  it('drops an expired session on 401', async () => {
    tokenStore.set('old')
    const expired = vi.fn()
    window.addEventListener('auth:expired', expired)
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify({ code: 'unauthorized', message: 'x' }), { status: 401 })))
    await api('/candidate/profile').catch(() => {})
    expect(tokenStore.get()).toBeNull()
    expect(expired).toHaveBeenCalled()
    window.removeEventListener('auth:expired', expired)
  })
})
