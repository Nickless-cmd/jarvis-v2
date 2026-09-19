import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, renderHook, act } from '@testing-library/react'
import * as api from '../../lib/api'
import { useTilbagespol } from '../../hooks/useTilbagespol'
import { TilbagespolBanner } from './TilbagespolBanner'
import { MessageActions } from '../rich/MessageActions'

/** Claude Desktop §8 (19/9-2026): spol tilbage, filerne røres ikke, fortryd til næste besked. */
const config = { apiBaseUrl: 'http://x', authToken: 't' } as api.ApiConfig

describe('useTilbagespol', () => {
  it('spoler tilbage, lægger teksten i skrivefeltet og genindlæser', async () => {
    const kald = vi.spyOn(api, 'apiFetch').mockResolvedValue({ rewind_id: 'rw-1', fjernet: 3, tekst: 'andet spørgsmål' })
    const genindlaes = vi.fn()
    const { result } = renderHook(() => useTilbagespol({ config, sessionId: 's1', genindlaes }))
    await act(async () => { await result.current.spol('m7') })
    expect(kald).toHaveBeenCalledWith(config, '/chat/sessions/s1/rewind', { method: 'POST', body: { message_id: 'm7' } })
    expect(result.current.tilbagespolet).toEqual({ rewindId: 'rw-1', fjernet: 3 })
    expect(result.current.indsaet?.tekst).toBe('andet spørgsmål')
    expect(genindlaes).toHaveBeenCalled()
    kald.mockRestore()
  })

  it('fortryd kalder undo og rydder feltet igen', async () => {
    const kald = vi.spyOn(api, 'apiFetch').mockResolvedValueOnce({ rewind_id: 'rw-1', fjernet: 2, tekst: 'x' }).mockResolvedValueOnce({ genskabt: 2 })
    const { result } = renderHook(() => useTilbagespol({ config, sessionId: 's1', genindlaes: () => {} }))
    await act(async () => { await result.current.spol('m7') })
    await act(async () => { await result.current.fortryd() })
    expect(kald).toHaveBeenLastCalledWith(config, '/chat/sessions/s1/rewind/rw-1/undo', { method: 'POST' })
    expect(result.current.tilbagespolet).toBeNull()
    expect(result.current.indsaet?.tekst).toBe('')
    kald.mockRestore()
  })

  it('serverens afslag vises (fx «fortryd lukkede ved næste besked»)', async () => {
    const kald = vi.spyOn(api, 'apiFetch').mockRejectedValue(new Error('Jarvis svarer stadig — stop svaret før du spoler tilbage'))
    const { result } = renderHook(() => useTilbagespol({ config, sessionId: 's1', genindlaes: () => {} }))
    await act(async () => { await result.current.spol('m7') })
    expect(result.current.fejl).toMatch(/stop svaret/)
    expect(result.current.tilbagespolet).toBeNull()
    kald.mockRestore()
  })
})

describe('banneret og knappen', () => {
  it('banneret lover det Claude Desktop lover — og Fortryd virker', () => {
    const onFortryd = vi.fn()
    render(<TilbagespolBanner fjernet={3} fejl="" onFortryd={onFortryd} onLuk={() => {}} />)
    expect(screen.getByTestId('tilbagespol-banner')).toHaveTextContent('3 beskeder fjernet. Dine filer er uændrede.')
    fireEvent.click(screen.getByRole('button', { name: 'Fortryd' }))
    expect(onFortryd).toHaveBeenCalled()
  })
  it('knappen findes kun når den gives', () => {
    const onRewind = vi.fn()
    const { rerender } = render(<MessageActions text="hej" onRewind={onRewind} />)
    fireEvent.click(screen.getByRole('button', { name: 'Spol tilbage hertil' }))
    expect(onRewind).toHaveBeenCalled()
    rerender(<MessageActions text="hej" />)
    expect(screen.queryByRole('button', { name: 'Spol tilbage hertil' })).toBeNull()
  })
})
