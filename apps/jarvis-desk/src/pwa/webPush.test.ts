/**
 * Web-push-abonnementet (side-67aea8c5b6).
 *
 * Kernen i beviset: abonnementet skal faktisk NÅ serveren. Et `PushSubscription`
 * der kun lever i browseren er værdiløst — uden POST til /push/web/subscribe
 * findes der intet at sende til, og fejlen er tavs (ingen push, ingen fejl).
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('../lib/api', () => ({ apiFetch: vi.fn() }))

import { apiFetch } from '../lib/api'
import { subscribeWebPush, webPushMulig } from './webPush'

function _stubSw(sub: unknown) {
  Object.defineProperty(navigator, 'serviceWorker', {
    configurable: true,
    value: {
      ready: Promise.resolve({
        pushManager: {
          getSubscription: () => Promise.resolve(sub),
          subscribe: () => Promise.resolve(sub),
        },
      }),
    },
  })
}

describe('webPush', () => {
  afterEach(() => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = undefined
    vi.mocked(apiFetch).mockReset()
  })

  it('er ikke muligt uden web-build (Electron har ingen push-tjeneste)', () => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = false
    expect(webPushMulig()).toBe(false)
  })

  it('POSTer endpoint og nøgler til /push/web/subscribe', async () => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = true
    Object.defineProperty(globalThis, 'PushManager', {
      configurable: true,
      value: function PushManager() {},
    })
    Object.defineProperty(globalThis, 'Notification', {
      configurable: true,
      value: { permission: 'granted' },
    })
    const sub = {
      endpoint: 'https://push.example/abc',
      toJSON: () => ({
        endpoint: 'https://push.example/abc',
        keys: { p256dh: 'P', auth: 'A' },
      }),
    }
    _stubSw(sub)
    vi.mocked(apiFetch).mockImplementation((_cfg, path) =>
      path === '/push/web/vapid'
        ? Promise.resolve({ key: 'BCp7' })
        : Promise.resolve({ ok: true }),
    )

    const ok = await subscribeWebPush({ apiBaseUrl: '', authToken: 't' })

    expect(ok).toBe(true)
    const kald = vi.mocked(apiFetch).mock.calls.find(([, p]) => p === '/push/web/subscribe')
    expect(kald).toBeTruthy()
    expect((kald?.[2] as { body: Record<string, string> }).body).toEqual({
      endpoint: 'https://push.example/abc',
      p256dh: 'P',
      auth: 'A',
    })
  })

  it('lader være når tilladelsen ikke er givet', async () => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = true
    Object.defineProperty(globalThis, 'PushManager', {
      configurable: true,
      value: function PushManager() {},
    })
    Object.defineProperty(globalThis, 'Notification', {
      configurable: true,
      value: { permission: 'denied' },
    })
    _stubSw(null)

    const ok = await subscribeWebPush({ apiBaseUrl: '', authToken: 't' })

    expect(ok).toBe(false)
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})
