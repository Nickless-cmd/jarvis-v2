import { describe, it, expect, afterEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useOnline } from './useOnline'

describe('useOnline', () => {
  afterEach(() => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })
  })

  it('starter fra navigator.onLine', () => {
    Object.defineProperty(navigator, 'onLine', { value: true, configurable: true })
    const { result } = renderHook(() => useOnline())
    expect(result.current).toBe(true)
  })

  it('reagerer på offline/online-events', () => {
    const { result } = renderHook(() => useOnline())
    act(() => { window.dispatchEvent(new Event('offline')) })
    expect(result.current).toBe(false)
    act(() => { window.dispatchEvent(new Event('online')) })
    expect(result.current).toBe(true)
  })
})
