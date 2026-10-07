import { useCallback, useEffect, useRef } from 'react'

export interface ClientEvents { focus_lost: number; away_ms: number; copies: number }

/**
 * What the test page records while a test is open — and tells the candidate about: switching away from
 * the tab (count and time away), copying the question text, time spent on each question while the tab
 * is visible, pasted answers. No camera, microphone or screen capture. The server combines these with
 * the response pattern into an integrity level (ok / attention / risk).
 */
export function useAttemptTracker(currentItem: number | undefined) {
  const s = useRef({
    focusLost: 0, awayMs: 0, copies: 0, awaySince: 0,
    item: undefined as number | undefined, itemStart: 0, spent: new Map<number, number>(), pasted: new Set<number>(),
  })

  // time on the current question accrues only while the tab is visible
  const flush = useCallback(() => {
    const st = s.current
    if (st.item !== undefined && !st.awaySince) st.spent.set(st.item, (st.spent.get(st.item) ?? 0) + (performance.now() - st.itemStart))
    st.itemStart = performance.now()
  }, [])

  useEffect(() => {
    flush()
    s.current.item = currentItem
  }, [currentItem, flush])

  useEffect(() => {
    const st = s.current
    const leave = () => {
      if (st.awaySince) return
      flush()
      st.focusLost += 1
      st.awaySince = performance.now()
    }
    const back = () => {
      if (!st.awaySince) return
      st.awayMs += performance.now() - st.awaySince
      st.awaySince = 0
      st.itemStart = performance.now()
    }
    const onVisibility = () => (document.hidden ? leave() : back())
    const onCopy = () => { st.copies += 1 }
    document.addEventListener('visibilitychange', onVisibility)
    window.addEventListener('blur', leave)
    window.addEventListener('focus', back)
    document.addEventListener('copy', onCopy)
    return () => {
      document.removeEventListener('visibilitychange', onVisibility)
      window.removeEventListener('blur', leave)
      window.removeEventListener('focus', back)
      document.removeEventListener('copy', onCopy)
    }
  }, [flush])

  /** Time on the question since the previous report (the server adds the reports up). */
  const takeTime = useCallback((itemId: number): number => {
    flush()
    const ms = s.current.spent.get(itemId) ?? 0
    s.current.spent.set(itemId, 0)
    return Math.round(ms)
  }, [flush])

  const markPaste = useCallback((itemId: number) => { s.current.pasted.add(itemId) }, [])
  const wasPasted = useCallback((itemId: number) => s.current.pasted.has(itemId), [])

  /** Cumulative counters; the server keeps the maximum, so a page reload cannot reset them. */
  const events = useCallback((): ClientEvents => {
    const st = s.current
    const away = st.awayMs + (st.awaySince ? performance.now() - st.awaySince : 0)
    return { focus_lost: st.focusLost, away_ms: Math.round(away), copies: st.copies }
  }, [])

  return { takeTime, markPaste, wasPasted, events }
}
