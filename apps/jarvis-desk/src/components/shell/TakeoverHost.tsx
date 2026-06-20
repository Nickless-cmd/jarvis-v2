import { useEffect, useReducer, useRef, useState } from 'react'
import { getActiveRuns, followRun, getSession } from '../../lib/api'
import { streamReducer, initialStreamState } from '../../lib/streamReducer'
import { MessageRow } from '../rich/MessageRow'
import { LivenessIndicator } from '../feedback/LivenessIndicator'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import type { ChatMessage } from '../../lib/api'

/**
 * App-niveau live takeover-panel: kører på tværs af ALLE faner — i modsætning til
 * ChatView's poll der kun lever i Chat-fanen. Når en chat-session får et aktivt run
 * (fx man tager over fra mobilen) MENS man er i Code/Cowork, popper et flydende
 * chat-vindue med PRÆCIS samme liveness som Chat mode: live transcript, spinner og
 * token-tæller.
 *
 * Mekanikken er kopieret 1:1 fra ChatView (den fungerende reference):
 * - bgUntil-LATCH (≥6s): et kort mobil-svar-run kan starte+slutte mellem to polls.
 *   Uden latchen rydder vi activeSid med det samme runnet forlader active-runs →
 *   panelet popper op og forsvinder igen INDEN follow/transcript når at vise noget
 *   (det var fejlen: "en notits der forsvinder når svaret er færdigt").
 * - followRun(/live) → followState: live token-stream (transcript + workingStep +
 *   output-token-estimat), samme kilde som ChatView's overlay.
 * - getSession-EFTERSLÆB: polles videre under latchen → fanger den persisterede,
 *   rensede besked når runnet slutter, så svaret bliver stående.
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
  const [elapsedMs, setElapsedMs] = useState(0)
  const startedAt = useRef(0)

  // 1) Find en cross-device-aktiv session — med 6s-latch (som ChatView) så korte
  //    runs ikke forsvinder mellem to polls.
  useEffect(() => {
    if (!settings) { setActiveSid(null); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    let bgUntil = 0
    let held: string | null = null
    const tick = async () => {
      try {
        const ids = await getActiveRuns(cfg)
        if (cancelled) return
        for (const d of [...dismissed.current]) if (!ids.includes(d)) dismissed.current.delete(d)
        // Chat OG code har nu native cross-device-liveness i selve viewet → ingen
        // popup der (Bjørn 2026-06-20). Popup'en er kun for øvrige flader.
        if (surface === 'chat' || surface === 'code') { held = null; setActiveSid(null); return }
        const cand = ids.find((id) => !dismissed.current.has(id)) ?? null
        if (cand) { held = cand; bgUntil = Date.now() + 6000 }
        else if (Date.now() >= bgUntil) { held = null }
        setActiveSid(held)
      } catch { /* behold sidste — ingen flicker */ }
    }
    void tick()
    const t = setInterval(tick, 1500)
    return () => { cancelled = true; clearInterval(t) }
  }, [settings, surface])

  // 2) Følg den aktive session live (token-stream). Genstart IKKE hvis vi følger.
  useEffect(() => {
    if (!settings || !activeSid) {
      followCtl.current?.abort(); followCtl.current = null
      return
    }
    if (followCtl.current) return
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    followCtl.current = followRun(cfg, activeSid, (ev) => followDispatch(ev), () => { followCtl.current = null })
    return () => { followCtl.current?.abort(); followCtl.current = null }
  }, [settings, activeSid])

  // 3) Poll transcript'en (efterslæb-kilde — fanger den persisterede besked).
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

  // 4) Elapsed-tæller til liveness-linjen (nulstil ved ny session).
  useEffect(() => {
    if (!activeSid) { setElapsedMs(0); return }
    startedAt.current = Date.now()
    setElapsedMs(0)
    const t = setInterval(() => setElapsedMs(Date.now() - startedAt.current), 1000)
    return () => clearInterval(t)
  }, [activeSid])

  if (!activeSid) return null
  const title = sessions.find((s) => s.id === activeSid)?.title || 'en samtale'
  const live = followState.status === 'working' && followState.blocks.length > 0
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
        {live ? (
          <MessageRow role="assistant" blocks={followState.blocks} density="compact" streaming />
        ) : lastAssistant ? (
          <MessageRow role="assistant" blocks={lastAssistant.content} density="compact" streaming={false} />
        ) : null}
        <LivenessIndicator
          status="working"
          elapsedMs={elapsedMs}
          density="compact"
          workingStep={followState.workingStep ?? 'vågner'}
          tokens={followState.usage.output}
        />
      </div>
    </div>
  )
}
