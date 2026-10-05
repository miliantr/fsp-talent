import { useCallback, useEffect, useRef, useState, type Dispatch, type SetStateAction } from 'react'
import { useI18n } from '../i18n/context'
import { api, errorMessage, type RequestOptions } from './client'

export interface ApiState<T> {
  data: T | null
  error: string | null
  loading: boolean
  reload: () => Promise<void>
  setData: Dispatch<SetStateAction<T | null>>
}

/** GET a resource; `path = null` skips the request. Re-fetches when `path`, `query` or the UI language
 * change (texts rendered by the server — explanations, reasons, reference names — follow the language). */
export function useApi<T>(path: string | null, query?: RequestOptions['query']): ApiState<T> {
  const { lang } = useI18n()
  const [data, setData] = useState<T | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState<boolean>(path !== null)
  const queryKey = JSON.stringify(query ?? {})
  const seq = useRef(0)

  const load = useCallback(async () => {
    if (path === null) return
    const id = ++seq.current
    setLoading(true)
    setError(null)
    try {
      const res = await api<T>(path, { query: JSON.parse(queryKey) })
      if (id === seq.current) setData(res)
    } catch (e) {
      if (id === seq.current) setError(errorMessage(e))
    } finally {
      if (id === seq.current) setLoading(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [path, queryKey, lang])

  useEffect(() => {
    void load()
  }, [load])

  return { data, error, loading, reload: load, setData }
}

/** Wraps a mutation with pending/error state. */
export function useAction<A extends unknown[], R>(fn: (...args: A) => Promise<R>) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const run = useCallback(async (...args: A): Promise<R | undefined> => {
    setPending(true)
    setError(null)
    try {
      return await fn(...args)
    } catch (e) {
      setError(errorMessage(e))
      return undefined
    } finally {
      setPending(false)
    }
  }, [fn])
  return { run, pending, error, setError }
}
