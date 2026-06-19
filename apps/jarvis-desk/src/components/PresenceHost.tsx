import { useEffect, useRef } from 'react'
import { useSettings } from '../hooks/useSettings'
import { presencePing, fetchPendingNotifications, ackNotification } from '../lib/api'
import { buildPingBody } from '../lib/presence'
import { consumeInteraction } from '../lib/presenceSignal'

/**
 * Altid-monteret (i shell'en) device-presence + proaktiv notif-poll. Skal IKKE
 * ligge i ChatView — den unmountes når man skifter fane, så presence ville stoppe
 * og routingen ramme forkert enhed. Her kører den mens appen er åben + logget ind.
 *
 * - Presence-ping hvert 5s: foreground (vindue-fokus) + awake (powerMonitor) +
 *   interaction (sat ved send via presenceSignal). device_key = installationens appId.
 * - Notif-poll hvert 3s: drain serverens desktop-kø → native OS-notifikation + ack.
 */
export function PresenceHost() {
  const { settings } = useSettings()
  const deviceKeyRef = useRef<string>('')

  useEffect(() => {
    if (!settings) return
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    const bridge = (window as unknown as {
      jarvisDesk?: {
        config?: { get?: () => Promise<{ appId?: string }> }
        isAwake?: () => Promise<boolean>
        notifyShow?: (kind: string, title: string, body: string) => void
        setActiveSession?: (sessionId: string | null) => void
      }
    }).jarvisDesk
    let cancelled = false

    const ensureKey = async (): Promise<string> => {
      if (deviceKeyRef.current) return deviceKeyRef.current
      try {
        const c = (await bridge?.config?.get?.()) || {}
        if (c.appId) { deviceKeyRef.current = c.appId; return c.appId }
      } catch { /* fald igennem */ }
      const key = (globalThis.crypto?.randomUUID?.() ?? `desk-${Date.now()}-${Math.floor(Math.random() * 1e9)}`)
      deviceKeyRef.current = key
      return key
    }

    const ping = async (): Promise<void> => {
      if (cancelled) return
      const key = await ensureKey()
      let awake = true
      try { awake = (await bridge?.isAwake?.()) ?? true } catch { /* default vågen */ }
      const body = buildPingBody({
        deviceKey: key,
        foreground: typeof document !== 'undefined' ? document.hasFocus() : true,
        awake,
        interaction: consumeInteraction(),
      })
      void presencePing(cfg, body)
    }

    const pollNotifs = async (): Promise<void> => {
      if (cancelled) return
      const items = await fetchPendingNotifications(cfg)
      if (cancelled || items.length === 0) return
      for (const it of items) {
        try { bridge?.notifyShow?.(it.kind, it.title || 'Jarvis', it.body || '') } catch { /* noop */ }
        if (it.session_id) { try { bridge?.setActiveSession?.(it.session_id) } catch { /* noop */ } }
        void ackNotification(cfg, it.notif_id)
      }
    }

    void ping()
    void pollNotifs()
    const pid = setInterval(() => { void ping() }, 5000)
    const nid = setInterval(() => { void pollNotifs() }, 3000)
    return () => { cancelled = true; clearInterval(pid); clearInterval(nid) }
  }, [settings])

  return null
}
