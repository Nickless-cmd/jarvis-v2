import { describe, it, expect, vi } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { usePollWhenVisible } from './usePollWhenVisible'

describe('usePollWhenVisible', () => {
  it('sætter data selv når fetcher-identiteten skifter ved hver re-render (Bjørn-bug)', async () => {
    // Simulér forælder der re-renderer konstant (live-puls) → ny fetcher-closure hver gang.
    let calls = 0
    const { result, rerender } = renderHook(
      ({ n }) => usePollWhenVisible(async () => { calls++; return `data-${n}` }, 10_000, true),
      { initialProps: { n: 0 } },
    )
    // mange re-renders med NY fetcher hver gang (som den konstante puls gjorde)
    for (let i = 1; i <= 5; i++) rerender({ n: i })
    await waitFor(() => expect(result.current.data).not.toBeNull())
    // poll-cyklussen blev IKKE revet ned af re-renders → data sat (ikke evig "Henter")
    expect(String(result.current.data)).toMatch(/^data-/)
    expect(calls).toBeGreaterThanOrEqual(1)
  })

  it('enabled=false → ingen fetch', () => {
    const fetcher = vi.fn().mockResolvedValue('x')
    renderHook(() => usePollWhenVisible(fetcher, 10_000, false))
    expect(fetcher).not.toHaveBeenCalled()
  })
})
