import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { useAttemptTracker } from './integrity'

let clock = 0
const setHidden = (hidden: boolean) => {
  Object.defineProperty(document, 'hidden', { configurable: true, get: () => hidden })
  document.dispatchEvent(new Event('visibilitychange'))
}

describe('test integrity tracker', () => {
  afterEach(() => vi.restoreAllMocks())

  it('counts leaving the tab once per absence and the time away', () => {
    vi.spyOn(performance, 'now').mockImplementation(() => clock)
    clock = 0
    const { result } = renderHook(() => useAttemptTracker(1))
    act(() => {
      clock = 10_000
      setHidden(true)
      window.dispatchEvent(new Event('blur')) // the same absence: counted once
      clock = 40_000
      setHidden(false)
      window.dispatchEvent(new Event('focus'))
    })
    expect(result.current.events()).toEqual({ focus_lost: 1, away_ms: 30_000, copies: 0 })
  })

  it('measures time on a question only while the tab is visible', () => {
    vi.spyOn(performance, 'now').mockImplementation(() => clock)
    clock = 0
    const { result, rerender } = renderHook(({ item }) => useAttemptTracker(item), { initialProps: { item: 1 } })
    act(() => {
      clock = 5_000
      setHidden(true)
      clock = 65_000
      setHidden(false)
      clock = 70_000
    })
    expect(result.current.takeTime(1)).toBe(10_000) // 5 s + 5 s, the minute away is not counted
    rerender({ item: 2 })
    clock = 82_000
    expect(result.current.takeTime(2)).toBe(12_000)
    expect(result.current.takeTime(1)).toBe(0) // reported already
  })

  it('records copies of the question text and pasted answers', () => {
    const { result } = renderHook(() => useAttemptTracker(3))
    act(() => {
      document.dispatchEvent(new Event('copy'))
      document.dispatchEvent(new Event('copy'))
      result.current.markPaste(3)
    })
    expect(result.current.events().copies).toBe(2)
    expect(result.current.wasPasted(3)).toBe(true)
    expect(result.current.wasPasted(4)).toBe(false)
  })
})
