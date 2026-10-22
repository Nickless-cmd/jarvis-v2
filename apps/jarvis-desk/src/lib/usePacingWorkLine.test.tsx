import { act, renderHook } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { usePacingWorkLine } from './usePacingWorkLine'

describe('usePacingWorkLine', () => {
  afterEach(() => vi.useRealTimers())

  it('lader korte synteser passere uden blink', () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(
      ({ pacing }) => usePacingWorkLine(pacing, 'run-1'),
      { initialProps: { pacing: true } },
    )
    act(() => vi.advanceTimersByTime(419))
    expect(result.current).toBe(false)
    rerender({ pacing: false })
    act(() => vi.advanceTimersByTime(1))
    expect(result.current).toBe(false)
  })

  it('skjuler efter tærsklen og viser straks ved catch-up', () => {
    vi.useFakeTimers()
    const { result, rerender } = renderHook(
      ({ pacing }) => usePacingWorkLine(pacing, 'run-1'),
      { initialProps: { pacing: true } },
    )
    act(() => vi.advanceTimersByTime(420))
    expect(result.current).toBe(true)
    rerender({ pacing: false })
    expect(result.current).toBe(false)
  })
})
