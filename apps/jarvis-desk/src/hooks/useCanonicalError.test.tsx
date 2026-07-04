import { describe, it, expect } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useCanonicalError } from './useCanonicalError'
import { StreamError } from '../lib/streamClient'

describe('useCanonicalError', () => {
  it('addFromEventPayload akkumulerer log + current', () => {
    const { result } = renderHook(() => useCanonicalError())
    act(() => result.current.addFromEventPayload({ code: 'self.cutoff', kind: 'self.cutoff', message: 'm', severity: 'error' }))
    expect(result.current.current?.kind).toBe('self.cutoff')
    expect(result.current.errors).toHaveLength(1)
  })

  it('nyeste-først + dismiss rydder current men beholder log', () => {
    const { result } = renderHook(() => useCanonicalError())
    act(() => result.current.addFromEventPayload({ code: 'a', kind: 'tool.timeout', message: 'a' }))
    act(() => result.current.addFromEventPayload({ code: 'b', kind: 'model.rate_limited', message: 'b' }))
    expect(result.current.errors[0]?.kind).toBe('model.rate_limited')
    act(() => result.current.dismiss())
    expect(result.current.current).toBeNull()
    expect(result.current.errors).toHaveLength(2)
  })

  it('addFromStreamError mapper StreamError → canonical (origin client)', () => {
    const { result } = renderHook(() => useCanonicalError())
    act(() => result.current.addFromStreamError(new StreamError('auth', 'x', { retryable: false })))
    expect(result.current.current?.origin).toBe('client')
    expect(result.current.current?.kind).toBe('auth.token_expired')
  })

  it('clear rydder alt', () => {
    const { result } = renderHook(() => useCanonicalError())
    act(() => result.current.addFromEventPayload({ code: 'a', kind: 'tool.timeout', message: 'a' }))
    act(() => result.current.clear())
    expect(result.current.errors).toHaveLength(0)
    expect(result.current.current).toBeNull()
  })
})
