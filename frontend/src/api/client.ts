const TOKEN_KEY = 'fsp_talent_token'

export class ApiError extends Error {
  status: number
  code: string
  details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.status = status
    this.code = code
    this.details = details
  }
}

export const tokenStore = {
  get(): string | null {
    try {
      return localStorage.getItem(TOKEN_KEY)
    } catch {
      return null
    }
  },
  set(token: string) {
    try {
      localStorage.setItem(TOKEN_KEY, token)
    } catch {
      /* storage unavailable: session-only auth */
    }
  },
  clear() {
    try {
      localStorage.removeItem(TOKEN_KEY)
    } catch {
      /* ignore */
    }
  },
}

type Query = Record<string, string | number | boolean | string[] | null | undefined>

export interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
  body?: unknown
  query?: Query
  form?: FormData
}

function buildQuery(query?: Query): string {
  if (!query) return ''
  const p = new URLSearchParams()
  for (const [k, v] of Object.entries(query)) {
    if (v === null || v === undefined || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => p.append(k, x))
    else p.append(k, String(v))
  }
  const s = p.toString()
  return s ? `?${s}` : ''
}

export async function api<T>(path: string, opts: RequestOptions = {}): Promise<T> {
  const headers: Record<string, string> = {}
  const token = tokenStore.get()
  if (token) headers.Authorization = `Bearer ${token}`
  let body: BodyInit | undefined
  if (opts.form) body = opts.form
  else if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }
  let res: Response
  try {
    res = await fetch(`/api${path}${buildQuery(opts.query)}`, { method: opts.method ?? 'GET', headers, body })
  } catch {
    throw new ApiError(0, 'network', 'Сервер недоступен. Проверьте, что backend запущен.')
  }
  if (res.status === 401 && token) {
    tokenStore.clear()
    window.dispatchEvent(new Event('auth:expired'))
  }
  const text = await res.text()
  const data = text ? JSON.parse(text) : null
  if (!res.ok) {
    throw new ApiError(res.status, data?.code ?? 'error', data?.message ?? data?.detail ?? `Ошибка ${res.status}`,
      data?.details ?? {})
  }
  return data as T
}

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message
  if (e instanceof Error) return e.message
  return 'Что-то пошло не так'
}
