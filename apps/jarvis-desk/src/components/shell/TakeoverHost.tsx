import { useEffect, useReducer, useRef, useState } from 'react'
import { getActiveRuns, followRun, getSession } from '../../lib/api'
import { streamReducer, initialStreamState } from '../../lib/streamReducer'
import { MessageRow } from '../rich/MessageRow'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import type { ChatMessage } from '../../lib/api'

/**
 * App-niveau live takeover-panel: kører på tværs af ALLE faner (Sidebar-stil) — i
 * modsætning til ChatView's poll der kun lever i Chat-fanen. Når en chat-session
 * får et aktivt run (fx man tager over fra mobilen) MENS man er i Code/Cowork,
 * popper et lille FLYDENDE chat-panel.
 *
 * For at matche Chat-fanens robusthed bruger panelet SAMME to kilder som ChatView:
 * (1) getSession-polling → transcript'en (vokser mens svaret persisteres; race-
 * sikkert selv for korte runs), og (2) /live-follow → token-stream live. Følgen
 * vises når den leverer; ellers den persisterede sidste assistant-besked + spinner.
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
  const [msgs, setMsgs] = useState<ChatMessage[]>([])

  // 1) Find en cross-device-aktiv session at vise (kun udenfor Chat-fanen).
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

  // 2) Følg den aktive session live (token-stream, når den leverer).
  useEffect(() => {
    if (!settings || !activeSid) { followCtl.current?.abort(); followCtl.current = null; return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    followCtl.current = followRun(cfg, activeSid, (ev) => followDispatch(ev), () => { followCtl.current = null })
    return () => { followCtl.current?.abort(); followCtl.current = null }
  }, [settings, activeSid])

  // 3) Poll transcript'en (race-sikker kilde — samme som ChatView's sessions.refresh).
  useEffect(() => {
    if (!settings || !activeSid) { setMsgs([]); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    const pull = async () => {
      try {
        const { messages } = await getSession(cfg, activeSid)
        if (!cancelled) setMsgs(messages)
      } catch { /* behold */ }
    }
    void pull()
    const t = setInterval(pull, 1200)
    return () => { cancelled = true; clearInterval(t) }
  }, [settings, activeSid])

  if (!activeSid) return null
  const title = sessions.find((s) => s.id === activeSid)?.title || 'en samtale'
  const streaming = followState.status === 'working' && followState.blocks.length > 0
  const lastAssistant = [...msgs].reverse().find((m) => m.role === 'assistant')
  return (
    <div className="takeover-live">
      <div className="takeover-live-head">
        <span className="takeover-live-title">
          🟢 {title} <span className="takeover-live-sub">— live fra en anden enhed</span>
        </span>
        <button type="button" className="takeover-live-open" onClick={() => { select(activeSid); setSurface('chat'); setActiveSid(null) }}>Åbn chat</button>
        <button type="button" className="takeover-live-x" aria-label="Skjul" onClick={() => { dismissed.current.add(activeSid); setActiveSid(null) }}>×</button>
      </div>
      <div className="takeover-live-body">
        {streaming ? (
          <MessageRow role="assistant" blocks={followState.blocks} density="compact" streaming />
        ) : lastAssistant ? (
          <MessageRow role="assistant" blocks={lastAssistant.content} density="compact" streaming={false} />
        ) : (
          <div className="takeover-live-wait">Jarvis arbejder…</div>
        )}
      </div>
    </div>
  )
}
