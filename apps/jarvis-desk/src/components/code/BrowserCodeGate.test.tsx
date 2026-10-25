import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { BrowserCodeGate } from './BrowserCodeGate'
import { SettingsContext, type SettingsContextValue } from '../../contexts/SettingsContext'
import * as devices from '../../lib/enheder'

const config = { apiBaseUrl: 'http://x', authToken: 'old-token' }

beforeEach(() => {
  localStorage.clear()
  vi.restoreAllMocks()
})

describe('BrowserCodeGate', () => {
  it('sender anmodningen til Desk og åbner først efter et godkendt token', async () => {
    vi.spyOn(devices, 'hentEnheder').mockResolvedValue({
      ok: true,
      data: {
        enheder: [], kraev_aktivt: true,
        denne: { type: 'ukendt', tilfoejet: false, kode_tilladt: false },
      },
    })
    vi.spyOn(devices, 'anmodOmBrowserAdgang').mockResolvedValue({
      ok: true, data: { request_id: 'req-1', state: 'pending', expires_in: 300 },
    })
    vi.spyOn(devices, 'hentBrowserAnmodningStatus').mockResolvedValue({
      ok: true, data: { state: 'approved', token: 'browser-token' },
    })
    const update = vi.fn().mockResolvedValue(undefined)
    const context: SettingsContextValue = {
      settings: { ...config, theme: 'dark', defaultModel: 'm', defaultThinking: 'think', trustDefault: 'ask' },
      auth: null, isConfigured: true, authStatus: 'ready', update,
    }
    render(
      <SettingsContext.Provider value={context}>
        <BrowserCodeGate config={config}><div>CODE READY</div></BrowserCodeGate>
      </SettingsContext.Provider>,
    )

    expect(await screen.findByText(/Godkend Code Mode i Jarvis Desk/)).toBeInTheDocument()
    await waitFor(() => expect(update).toHaveBeenCalledWith({ authToken: 'browser-token' }))
    expect(await screen.findByText('CODE READY')).toBeInTheDocument()
  })
  it('lukker IKKE ind naar Desk afviser — og gemmer intet token', async () => {
    vi.spyOn(devices, 'hentEnheder').mockResolvedValue({
      ok: true,
      data: {
        enheder: [], kraev_aktivt: true,
        denne: { type: 'ukendt', tilfoejet: false, kode_tilladt: false },
      },
    })
    vi.spyOn(devices, 'anmodOmBrowserAdgang').mockResolvedValue({
      ok: true, data: { request_id: 'req-2', state: 'pending', expires_in: 300 },
    })
    vi.spyOn(devices, 'hentBrowserAnmodningStatus').mockResolvedValue({
      ok: true, data: { state: 'denied' },
    })
    const update = vi.fn().mockResolvedValue(undefined)
    const context: SettingsContextValue = {
      settings: { ...config, theme: 'dark', defaultModel: 'm', defaultThinking: 'think', trustDefault: 'ask' },
      auth: null, isConfigured: true, authStatus: 'ready', update,
    }
    render(
      <SettingsContext.Provider value={context}>
        <BrowserCodeGate config={config}><div>CODE READY</div></BrowserCodeGate>
      </SettingsContext.Provider>,
    )

    expect(await screen.findByText(/afviste anmodningen/i)).toBeInTheDocument()
    expect(screen.queryByText('CODE READY')).toBeNull()
    expect(update).not.toHaveBeenCalled()
  })

  it('aabner uden anmodning naar der ikke kraeves enhed', async () => {
    const anmod = vi.spyOn(devices, 'anmodOmBrowserAdgang')
    vi.spyOn(devices, 'hentEnheder').mockResolvedValue({
      ok: true,
      data: {
        enheder: [], kraev_aktivt: false,
        denne: { type: 'ukendt', tilfoejet: false, kode_tilladt: true },
      },
    })
    const update = vi.fn().mockResolvedValue(undefined)
    const context: SettingsContextValue = {
      settings: { ...config, theme: 'dark', defaultModel: 'm', defaultThinking: 'think', trustDefault: 'ask' },
      auth: null, isConfigured: true, authStatus: 'ready', update,
    }
    render(
      <SettingsContext.Provider value={context}>
        <BrowserCodeGate config={config}><div>CODE READY</div></BrowserCodeGate>
      </SettingsContext.Provider>,
    )

    expect(await screen.findByText('CODE READY')).toBeInTheDocument()
    expect(anmod).not.toHaveBeenCalled()
  })
})
