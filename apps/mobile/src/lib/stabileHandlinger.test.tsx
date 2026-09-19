import { renderHook } from '@testing-library/react-native'
import { useRaekkeFn, useSenesteFn } from './stabileHandlinger'

describe('stabile handlinger til memoiserede rækker', () => {
  it('useSenesteFn: samme identitet over renders, men kalder den SENESTE udgave', async () => {
    const a = jest.fn(); const b = jest.fn()
    const { result, rerender } = await renderHook(({ fn }: { fn: () => void }) => useSenesteFn(fn), {
      initialProps: { fn: a }
    })
    const foerste = result.current
    await rerender({ fn: b })
    expect(result.current).toBe(foerste)
    result.current()
    expect(a).not.toHaveBeenCalled()
    expect(b).toHaveBeenCalledTimes(1)
  })

  it('useRaekkeFn: én stabil funktion pr. id, der kalder den seneste fn(id)', async () => {
    const a = jest.fn(); const b = jest.fn()
    const { result, rerender } = await renderHook(({ fn }: { fn: (id: string) => void }) => useRaekkeFn(fn), {
      initialProps: { fn: a }
    })
    const f1 = result.current('m1')
    expect(result.current('m1')).toBe(f1)
    expect(result.current('m2')).not.toBe(f1)
    await rerender({ fn: b })
    expect(result.current('m1')).toBe(f1)
    f1()
    expect(b).toHaveBeenCalledWith('m1')
    expect(a).not.toHaveBeenCalled()
  })
})
