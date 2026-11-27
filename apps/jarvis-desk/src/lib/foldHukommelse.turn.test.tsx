import { act, renderHook } from '@testing-library/react'
import { beforeEach, expect, it } from 'vitest'
import { laesFold, rydFoldHukommelse, useFoldHukommelse } from './foldHukommelse'
beforeEach(rydFoldHukommelse)
it('a new turn never returns the previous manual fold, even in its first render', () => {
  const seen: Array<boolean | null> = []
  const { result, rerender } = renderHook(({ run, turn }: { run?: string; turn: string }) => {
    const state = useFoldHukommelse(run, turn)
    seen.push(state[0])
    return state
  }, { initialProps: { run: 'old-run', turn: 'old-turn' } as { run?: string; turn: string } })
  act(() => result.current[1](false))
  seen.length = 0
  rerender({ run: undefined, turn: 'manual-turn' })
  expect(seen.every((value) => value === null)).toBe(true)
  expect(result.current[0]).toBeNull()
  rerender({ run: 'manual-run', turn: 'manual-turn' })
  expect(result.current[0]).toBeNull()
  act(() => result.current[1](true))
  rerender({ run: 'followup-run', turn: 'manual-turn' })
  expect(result.current[0]).toBe(true)
  expect(laesFold('followup-run')).toBe(true)
  seen.length = 0
  rerender({ run: 'autonomous-run', turn: 'autonomous-turn' })
  expect(seen.every((value) => value === null)).toBe(true)
})
