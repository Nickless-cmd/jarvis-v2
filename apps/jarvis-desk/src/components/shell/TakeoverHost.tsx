import { useEffect, useRef, useState } from 'react'
import { getActiveRuns } from '../../lib/api'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'

/**
 * App-niveau takeover-notits: kører på tværs af ALLE faner (Sidebar-stil) — i
 * modsætning til ChatView's poll der kun lever i Chat-fanen. Når en chat-session
 * får et aktivt run (fx man tager over fra mobilen) MENS man er i Code/Cowork,
 * popper en lille notits med "Åbn chat" der skifter til Chat-fanen + den session.
 * I selve Chat-fanen håndterer ChatView det (live-follow + takeover-banner), så
 * her notificerer vi KUN når surface !== 'chat'.
 */
export function TakeoverHost({
  surface,
  setSurface
}: {
  surface: string
  setSurface: (s: 'chat') => void
}) {
  const { sessions, select } = useSessions()
  const { settings } = useSettings()
  const [notifySid, setNotifySid] = useState<string | null>(null)
  const dismissed = useRef<Set<string>>(new Set())

  useEffect(() => {
    if (!settings) {
      setNotifySid(null)
      return
    }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    const tick = async () => {
      try {
        const ids = await getActiveRuns(cfg)
        if (cancelled) return
        // Ryd dismissed for sessioner der ikke længere er aktive → ny aktivitet
        // senere notificerer igen.
        for (const d of [...dismissed.current]) if (!ids.includes(d)) dismissed.current.delete(d)
        // I Chat-fanen håndterer ChatView det selv.
        if (surface === 'chat') {
          setNotifySid(null)
          return
        }
        setNotifySid(ids.find((id) => !dismissed.current.has(id)) ?? null)
      } catch {
        /* behold sidste — netværks-blip */
      }
    }
    void tick()
    const t = setInterval(tick, 2500)
    return () => {
      cancelled = true
      clearInterval(t)
    }
  }, [settings, surface])

  if (!notifySid) return null
  const title = sessions.find((s) => s.id === notifySid)?.title || 'en samtale'
  return (
    <div className="takeover-toast" role="status">
      <span className="takeover-toast-text">📱 Aktivitet i “{title}” — fra en anden enhed</span>
      <button
        type="button"
        className="takeover-toast-open"
        onClick={() => {
          select(notifySid)
          setSurface('chat')
          setNotifySid(null)
        }}
      >
        Åbn chat
      </button>
      <button
        type="button"
        className="takeover-toast-x"
        aria-label="Skjul"
        onClick={() => {
          dismissed.current.add(notifySid)
          setNotifySid(null)
        }}
      >
        ×
      </button>
    </div>
  )
}
