import { act, renderHook } from '@testing-library/react-native'
import { usePacingWorkLine } from './usePacingWorkLine'

describe('usePacingWorkLine', () => {
  afterEach(() => jest.useRealTimers())

  it('ignorerer korte synteser', async () => {
    jest.useFakeTimers()
    const { result, rerender } = await renderHook(
      ({ pacing }: { pacing: boolean }) => usePacingWorkLine(pacing, 'run-1'),
      { initialProps: { pacing: true } },
    )
    await act(async () => jest.advanceTimersByTime(419))
    expect(result.current).toBe(false)
    await rerender({ pacing: false })
    await act(async () => jest.advanceTimersByTime(1))
    expect(result.current).toBe(false)
  })

  it('skjuler efter tærsklen og viser straks ved catch-up', async () => {
    jest.useFakeTimers()
    const { result, rerender } = await renderHook(
      ({ pacing }: { pacing: boolean }) => usePacingWorkLine(pacing, 'run-1'),
      { initialProps: { pacing: true } },
    )
    await act(async () => jest.advanceTimersByTime(420))
    expect(result.current).toBe(true)
    await rerender({ pacing: false })
    expect(result.current).toBe(false)
  })
})
