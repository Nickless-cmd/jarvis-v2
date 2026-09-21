import { act, renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import { useSettingsResource } from './useSettingsResource'
// «first»/«second» er raekkefoelge-maerker, ikke noegler: testen handler om
// at hook'en SKIFTER konto, saa de to vaerdier skal bare vaere forskellige.
const config = { apiBaseUrl: 'https://example.test', authToken: 'first' } // noqa: literal-credential
describe('useSettingsResource', () => {
  it('recovers from failure and does not confuse failure with an empty list', async () => {
    const load = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValue([])
    const { result } = renderHook(() => useSettingsResource(config, load))
    await waitFor(() => expect(result.current.status).toBe('error'))
    expect(result.current.data).toBeNull()
    act(() => result.current.retry())
    await waitFor(() => expect(result.current.status).toBe('ready'))
    expect(result.current.data).toEqual([])
  })
  it('ignores an old account response after credentials change', async () => {
    let resolveOld!: (value: string) => void
    const old = new Promise<string>(resolve => { resolveOld = resolve })
    const load = vi.fn().mockReturnValueOnce(old).mockResolvedValue('new-account')
    const { result, rerender } = renderHook(({ token }) => useSettingsResource({ ...config, authToken: token }, load), { initialProps: { token: 'first' } }) // noqa: literal-credential
    await waitFor(() => expect(load).toHaveBeenCalledTimes(1))
    rerender({ token: 'second' }) // noqa: literal-credential
    await waitFor(() => expect(result.current.data).toBe('new-account'))
    await act(async () => resolveOld('old-account'))
    expect(result.current.data).toBe('new-account')
  })
  it('shows missing connection without a request', () => {
    const load = vi.fn()
    const { result } = renderHook(() => useSettingsResource(undefined, load))
    expect(result.current.status).toBe('missing')
    expect(load).not.toHaveBeenCalled()
  })
})
