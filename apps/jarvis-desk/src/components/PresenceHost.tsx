import { useEffect, useRef } from 'react'
import { useSettings } from '../hooks/useSettings'
import { presencePing, fetchPendingNotifications, ackNotification } from '../lib/api'
import { buildPingBody } from '../lib/presence'
import { consumeInteraction } from '../lib/presenceSignal'
import { loadMode, getDesktopLocation, type DeskLocationPayload } from '../lib/deskLocation'

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

    // Lokation: cache i 10 min (IP/manuel ændrer sig sjældent; browser-GPS pollet
    // hvert 5 min via maximumAge). clearedOff sender {} ÉN gang ved toggle off.
    let cachedLoc: DeskLocationPayload | null = null
    let cachedAt = 0
    let clearedOff = false
    const resolveLocation = async (): Promise<DeskLocationPayload | Record<string, never> | undefined> => {
      const mode = loadMode()
      if (mode === 'off') {
        cachedLoc = null
        if (clearedOff) return undefined
        clearedOff = true
        return {}
      }
      clearedOff = false
      const now = Date.now()
      if (cachedLoc && now - cachedAt < 600000) return cachedLoc
      const loc = await getDesktopLocation(mode)
      if (loc) { cachedLoc = loc; cachedAt = now; return loc }
      return cachedLoc ?? undefined
    }

    const ping = async (): Promise<void> => {
      if (cancelled) return
      const key = await ensureKey()
      let awake = true
      try { awake = (await bridge?.isAwake?.()) ?? true } catch { /* default vågen */ }
      const location = await resolveLocation()
      if (cancelled) return
      const body = buildPingBody({
        deviceKey: key,
        foreground: typeof document !== 'undefined' ? document.hasFocus() : true,
        awake,
        interaction: consumeInteraction(),
        location,
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
