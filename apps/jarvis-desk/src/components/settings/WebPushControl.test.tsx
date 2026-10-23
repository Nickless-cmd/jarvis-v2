import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { WebPushControl } from './WebPushControl'

const subscribe = vi.fn()
const unsubscribe = vi.fn()
const mulig = vi.fn()

vi.mock('../../pwa/webPush', () => ({
  subscribeWebPush: (...a: unknown[]) => subscribe(...a),
  unsubscribeWebPush: (...a: unknown[]) => unsubscribe(...a),
  webPushMulig: () => mulig(),
}))

const cfg = { apiBaseUrl: 'https://jarvis.example', authToken: 'token' }

function tilladelse(permission: NotificationPermission) {
  Object.defineProperty(globalThis, 'Notification', {
    configurable: true,
    value: { permission },
  })
}

describe('WebPushControl', () => {
  beforeEach(() => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = true
    mulig.mockReset().mockReturnValue(true)
    subscribe.mockReset().mockResolvedValue(true)
    unsubscribe.mockReset().mockResolvedValue(true)
    tilladelse('default')
  })

  it('aktiverer først fra brugerens tryk', async () => {
    render(<WebPushControl config={cfg} />)
    const knap = await screen.findByRole('button', { name: 'Aktivér notifikationer' })
    expect(subscribe).not.toHaveBeenCalled()
    await userEvent.click(knap)
    await waitFor(() => expect(subscribe).toHaveBeenCalledWith(cfg))
    expect(await screen.findByText(/Aktiv — Jarvis kan nå/)).toBeInTheDocument()
  })

  it('forklarer hjemmeskærmskravet når push ikke er tilgængelig', async () => {
    mulig.mockReturnValue(false)
    render(<WebPushControl config={cfg} />)
    expect(await screen.findByText(/Åbn Jarvis fra hjemmeskærmen/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Aktivér notifikationer' })).toBeDisabled()
  })

  it('viser leveringsfejl selv hvis browseren nåede at oprette abonnementet', async () => {
    subscribe.mockResolvedValue(false)
    tilladelse('granted')
    Object.defineProperty(navigator, 'serviceWorker', {
      configurable: true,
      value: { ready: Promise.resolve({ pushManager: { getSubscription: vi.fn().mockResolvedValue({ endpoint: 'lokal' }) } }) },
    })
    render(<WebPushControl config={cfg} />)
    await userEvent.click(await screen.findByRole('button', { name: 'Deaktivér på denne enhed' }))
    await userEvent.click(await screen.findByRole('button', { name: 'Aktivér notifikationer' }))
    expect(await screen.findByText(/Kunne ikke opdatere/)).toBeInTheDocument()
  })
})
