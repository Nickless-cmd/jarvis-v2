import { useEffect, useReducer, useRef, useState } from 'react'
import { getActiveRuns, followRun } from '../../lib/api'
import { streamReducer, initialStreamState } from '../../lib/streamReducer'
import { MessageRow } from '../rich/MessageRow'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'

/**
 * App-niveau live takeover-panel: kører på tværs af ALLE faner (Sidebar-stil) — i
 * modsætning til ChatView's poll der kun lever i Chat-fanen. Når en chat-session
 * får et aktivt run (fx man tager over fra mobilen) MENS man er i Code/Cowork,
 * popper et lille FLYDENDE chat-panel der FØLGER runnet live (samme /live-stream
 * som ChatView) — tokens streamer ind + spinner — så man får hele oplevelsen uden
 * at forlade Code. "Åbn chat" skifter til Chat-fanen + den session. I selve
 * Chat-fanen håndterer ChatView det selv (surface==='chat' → vi gør intet).
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
  const [activeSid, setActiveSid] = useState<string | null>(null)
  const dismissed = useRef<Set<string>>(new Set())
  const [followState, followDispatch] = useReducer(streamReducer, undefined, initialStreamState)
  const followCtl = useRef<{ abort: () => void } | null>(null)

  // 1) Poll: find en cross-device-aktiv session at vise (kun udenfor Chat-fanen).
  useEffect(() => {
    if (!settings) { setActiveSid(null); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    const tick = async () => {
      try {
        const ids = await getActiveRuns(cfg)
        if (cancelled) return
        for (const d of [...dismissed.current]) if (!ids.includes(d)) dismissed.current.delete(d)
        if (surface === 'chat') { setActiveSid(null); return }
        setActiveSid(ids.find((id) => !dismissed.current.has(id)) ?? null)
      } catch { /* behold sidste */ }
    }
    void tick()
    const t = setInterval(tick, 2000)
    return () => { cancelled = true; clearInterval(t) }
  }, [settings, surface])

  // 2) Følg den aktive session live (samme /live-stream som ChatView's followState).
  useEffect(() => {
    if (!settings || !activeSid) {
      followCtl.current?.abort(); followCtl.current = null
      return
    }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    followCtl.current = followRun(cfg, activeSid, (ev) => followDispatch(ev), () => { followCtl.current = null })
    return () => { followCtl.current?.abort(); followCtl.current = null }
  }, [settings, activeSid])

  if (!activeSid) return null
  const title = sessions.find((s) => s.id === activeSid)?.title || 'en samtale'
  const streaming = followState.status === 'working'
  return (
    <div className="takeover-live">
      <div className="takeover-live-head">
        <span className="takeover-live-title">
          {streaming ? '🟢' : '📱'} {title} <span className="takeover-live-sub">— live fra en anden enhed</span>
        </span>
        <button type="button" className="takeover-live-open" onClick={() => { select(activeSid); setSurface('chat'); setActiveSid(null) }}>Åbn chat</button>
        <button type="button" className="takeover-live-x" aria-label="Skjul" onClick={() => { dismissed.current.add(activeSid); setActiveSid(null) }}>×</button>
      </div>
      <div className="takeover-live-body">
        {followState.blocks.length > 0 ? (
          <MessageRow role="assistant" blocks={followState.blocks} density="compact" streaming={streaming} />
        ) : (
          <div className="takeover-live-wait">Jarvis arbejder…</div>
        )}
      </div>
    </div>
  )
}
