import { useEffect, useReducer, useRef, useState } from 'react'
import { ArrowDown, PanelRight } from 'lucide-react'
import { streamReducer, initialStreamState } from '../lib/streamReducer'
import { useSessions } from '../hooks/useSessions'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { usePanel } from '../hooks/usePanel'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { getContextInfo, getActiveRuns, followRun } from '../lib/api'
import { PresenceDot } from '../components/shell/PresenceDot'
import { ConnectionPill } from '../components/shell/ConnectionPill'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'

const NEAR_BOTTOM_PX = 120

/** Chat-mode. Ved tom/ny samtale: composer centreret midt på skærmen. Ved
 *  første besked oprettes session (hvis nødvendigt) og layoutet skifter — composer
 *  hopper ned i bunden, transcript fylder. */
export function ChatView({ sessionId }: { sessionId: string | null }) {
  const sessions = useSessions()
  const stream = useStream()
  const { settings, auth } = useSettings()
  const panel = usePanel()
  const reconciledForRun = useRef<string | null>(null)
  const transcriptRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)
  const [compactAt, setCompactAt] = useState(0)
  // Autonomt baggrunds-run (fx operator_wakeup) i NETOP denne session — som
  // klienten ikke selv driver. Når det opdages, vis at Jarvis arbejder + hent
  // nye beskeder ind, så han "kalder op" i appen (Bjørn 2026-06-13).
  const [bgActive, setBgActive] = useState(false)
  // Follow-stream: token-stream et autonomt wakeup-runs svar live (i stedet for
  // at "dumpe" det ind når det er færdigt). Egen reducer fodret af /follow-SSE'en.
  const [followState, followDispatch] = useReducer(streamReducer, undefined, initialStreamState)
  const followCtrlRef = useRef<{ abort: () => void } | null>(null)

  // Context-ring (#9): hent autocompact-tærsklen én gang.
  useEffect(() => {
    if (!settings) return
    getContextInfo({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken })
      .then((r) => setCompactAt(r.compact_at))
      .catch(() => setCompactAt(0))
  }, [settings])

  // Context-ring: vis det RIGTIGE niveau fra start. Når en tur slutter kender
  // vi de ægte kontekst-tokens (usage.input + cache) — vi gemmer dem pr. session
  // i localStorage, så de vises straks ved genåbning (i stedet for tom ring).
  const [seededTokens, setSeededTokens] = useState(0)
  useEffect(() => {
    const v = sessionId ? Number(localStorage.getItem(`jarvis-desk:ctx:${sessionId}`) || '0') : 0
    setSeededTokens(Number.isFinite(v) ? v : 0)
  }, [sessionId])
  const liveTokens = stream.usage.input + stream.usage.cacheHit
  useEffect(() => {
    if (sessionId && liveTokens > 0) {
      localStorage.setItem(`jarvis-desk:ctx:${sessionId}`, String(liveTokens))
      setSeededTokens(liveTokens)
    }
  }, [liveTokens, sessionId])
  const contextTokens = Math.max(liveTokens, seededTokens)

  useEffect(() => { if (sessionId) sessions.select(sessionId) }, [sessionId])

  // Fortæl main-processen hvilken session der er fremme, så en operator_wakeup
  // re-engagerer i NETOP denne desk-samtale (ikke en frisk/Discord).
  useEffect(() => {
    const b = (window as unknown as { jarvisDesk?: { setActiveSession?: (s: string | null) => void } }).jarvisDesk
    b?.setActiveSession?.(sessionId)
  }, [sessionId])

  // Pickup af autonome baggrunds-runs (operator_wakeup mv.): poll backend for
  // om DENNE session har et aktivt run vi ikke selv driver. Mens det kører:
  // vis liveness + hent nye beskeder ind, så Jarvis' selv-startede svar dukker
  // op live i appen i stedet for at kræve et manuelt session-skift.
  useEffect(() => {
    if (!settings || !sessionId) { setBgActive(false); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    // Häng-detektor: antal polls i træk hvor VI tror vi streamer denne session,
    // men serveren IKKE har et aktivt run for den.
    let staleMisses = 0
    // Efterslæb: bliv ved med at hente et par gange EFTER et baggrunds-run
    // slutter, så en sent-persisteret besked også fanges (ikke kun én hentning).
    let cooldown = 0
    // Latch: et autonomt wakeup-run kan være SÅ kort (~3s, én besked) at det
    // starter+slutter mellem to polls → ring/systray/header (drevet af bgActive)
    // ville aldrig nå at reagere. Når et run ses, hold bgActive i ≥6s så
    // indikatorerne reagerer synligt (Bjørn 2026-06-13).
    let bgUntil = 0
    const tick = () => {
      void getActiveRuns(cfg)
        .then((ids) => {
          if (cancelled) return
          const serverHasRun = ids.includes(sessionId)
          // 'working' = vi driver selv et run → ikke et baggrunds-run.
          const active = serverHasRun && stream.status !== 'working'
          if (active) bgUntil = Date.now() + 6000
          setBgActive(active || Date.now() < bgUntil)
          if (active) { cooldown = 3; void sessions.refresh() }       // mens det kører
          else if (cooldown > 0) { cooldown -= 1; void sessions.refresh() } // efterslæb

          // HÄNG-DETEKTOR (Bjørn 2026-06-13: "han døde midt i et run, tænkte
          // hænger"): hvis vi tror vi streamer DENNE session men serveren ikke
          // har noget aktivt run for den i 3 polls i træk (~9s), døde runnet
          // server-side (proces-/loop-død) UDEN at sende message_stop — så
          // backendens finally-garanti nåede aldrig at køre. Tving terminal,
          // så liveness/thinking ikke hænger på 'working'. 9s-vinduet undgår
          // falsk-positiv lige efter run-start før serveren har registreret det.
          if (stream.status === 'working' && stream.workingSessionId === sessionId && !serverHasRun) {
            staleMisses += 1
            if (staleMisses >= 3) { staleMisses = 0; void stream.abort() }
          } else {
            staleMisses = 0
          }
        })
        .catch(() => { /* behold sidste — ingen flicker ved netværks-blip */ })
    }
    tick()
    const id = setInterval(tick, 1500) // hurtigere → fanger korte autonome runs
    return () => { cancelled = true; clearInterval(id) }
  }, [settings, sessionId, stream.status, stream.workingSessionId])

  useEffect(() => {
    if (stream.status === 'done' && stream.blocks.length > 0 && reconciledForRun.current !== stream.activeRunId) {
      reconciledForRun.current = stream.activeRunId
      sessions.reconcile({
        id: `a-${stream.activeRunId ?? Date.now()}`,
        role: 'assistant',
        content: stream.blocks,
        created_at: new Date().toISOString(),
        parent_id: null,
      })
      // Hent serverens GEMTE (rensede + normaliserede) besked og lad den overtage
      // placeholderen. Backend-guarden kan have erstattet/sanitizeret en tool-echo-
      // leak, og normalizer'en har struktureret teksten — det er den version der
      // skal stå, ikke vores rå live-stream. To forsøg dækker persist-latency.
      const t1 = setTimeout(() => { void sessions.refresh() }, 700)
      const t2 = setTimeout(() => { void sessions.refresh() }, 2200)
      return () => { clearTimeout(t1); clearTimeout(t2) }
    }
    return undefined
  }, [stream.status])

  // Systray-spinner ved autonomt baggrunds-run (StreamContext styrer egne runs).
  // Får trayState='working' så ikonet drejer ligesom ved et normalt run.
  useEffect(() => {
    if (!bgActive) return
    const b = (window as unknown as { jarvisDesk?: { setActiveRun?: (id: string | null) => void } }).jarvisDesk
    b?.setActiveRun?.('autonomous')
    return () => { b?.setActiveRun?.(null) }
  }, [bgActive])

  // Follow-stream MIDLERTIDIGT DEAKTIVERET (2026-06-13): backend-follow er
  // rullet tilbage (translate-i-tråd brækkede run-livscyklus). Når desk'en åbnede
  // /follow alligevel, gav den abort-støj ("BodyStreamBuffer was aborted") når
  // forbindelsen blev lukket — og den hentede aldrig frames. Genaktiveres med
  // translate-i-ENDPOINT-redesignet (se memory project_autonomous_run_followstream).
  const FOLLOW_ENABLED = false
  useEffect(() => {
    if (!FOLLOW_ENABLED || !bgActive || !sessionId || !settings) return
    if (followCtrlRef.current) return // følger allerede
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    followCtrlRef.current = followRun(
      cfg, sessionId,
      (ev) => followDispatch(ev),
      () => { followCtrlRef.current = null },
    )
    return () => { followCtrlRef.current?.abort(); followCtrlRef.current = null }
  }, [bgActive, sessionId, settings])

  const scrollToBottom = () => {
    const el = transcriptRef.current
    if (el) el.scrollTop = el.scrollHeight
    setUnread(0)
  }

  const onScroll = () => {
    const el = transcriptRef.current
    if (!el) return
    const near = el.scrollHeight - el.scrollTop - el.clientHeight < NEAR_BOTTOM_PX
    setAtBottom(near)
    if (near) setUnread(0)
  }

  const lastScrolledSession = useRef<string | null>(null)
  useEffect(() => {
    const el = transcriptRef.current
    if (!el) return
    const isNewSession = lastScrolledSession.current !== sessionId
    if (isNewSession) {
      el.scrollTop = el.scrollHeight
      if (sessions.messages.length > 0) lastScrolledSession.current = sessionId
      setUnread(0)
      return
    }
    if (atBottom) el.scrollTop = el.scrollHeight
    else setUnread((u) => u + 1)
  }, [sessions.messages.length, sessionId])

  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
  }, [stream.blocks, followState.blocks, atBottom])

  const doSend = async (text: string, opts: ComposerSendOpts) => {
    let sid = sessionId
    if (!sid) {
      const created = await sessions.create('Ny samtale')
      sid = created.id
    }
    // v2-stream kræver en ikke-tom besked. Ved billede-kun send bruges filnavnene
    // som fallback-tekst (backend afviser ellers med 400). Jarvis ser endnu ikke
    // selve billedet — vision-wiring i start_visible_run er en separat backend-opgave.
    const message = text.trim() || opts.attachments.map((a) => a.name).join(', ') || 'Vedhæftet'
    const imageBlocks = opts.attachments
      .filter((a) => a.isImage && a.src)
      .map((a) => ({ type: 'image' as const, src: a.src as string, alt: a.name }))
    const content = [
      ...(text.trim() ? [{ type: 'text' as const, text }] : []),
      ...imageBlocks,
      ...(!text.trim() && imageBlocks.length === 0 ? [{ type: 'text' as const, text: message }] : []),
    ]
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    setAtBottom(true)
    setUnread(0)
    stream.send(message, {
      sessionId: sid,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
      model: opts.model,
      providerChoice: opts.providerChoice,
    })
  }

  const streaming = stream.status === 'working'

  // Follow-up kø: skriver man mens Jarvis streamer, lægges beskeden i kø og
  // sendes automatisk når turen er færdig (done). Deterministisk — ikke nudge.
  const [queued, setQueued] = useState<{ text: string; opts: ComposerSendOpts } | null>(null)
  const handleSend = (text: string, opts: ComposerSendOpts) => {
    if (streaming) setQueued({ text, opts })
    else void doSend(text, opts)
  }
  useEffect(() => {
    if (stream.status === 'done' && queued) {
      const q = queued
      setQueued(null)
      void doSend(q.text, q.opts)
    }
  }, [stream.status, queued])

  const visibleMessages = sessions.messages.filter((m) => m.role === 'user' || m.role === 'assistant')
  const isEmpty =
    !sessionId ||
    (visibleMessages.length === 0 && stream.status === 'idle' && stream.blocks.length === 0 && !queued && !bgActive)

  const ensureSessionId = async () => {
    if (sessionId) return sessionId
    const created = await sessions.create('Ny samtale')
    return created.id
  }

  const composer = (
    <Composer
      streaming={streaming}
      onSend={handleSend}
      onStop={() => void stream.abort()}
      model="deepseek-flash"
      thinking="think"
      config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
      getSessionId={ensureSessionId}
      showPermissions={false}
      contextTokens={contextTokens}
      compactAt={compactAt}
      isOwner={auth?.role === 'owner'}
    />
  )

  const activeSession = sessions.sessions.find((s) => s.id === sessionId)
  const chatTitle = activeSession?.title || (isEmpty ? 'Ny samtale' : 'Samtale')
  const header = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={bgActive && stream.status !== 'working' ? 'working' : stream.status} /> <span className="chat-title">{chatTitle}</span>
      </div>
      <div className="chatview-head-right">
        {settings && (
          <ConnectionPill config={{ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }} />
        )}
        <button
          type="button"
          className={`panel-toggle ${panel.open ? 'active' : ''}`}
          aria-label="Vis/skjul panel"
          title="Panel"
          onClick={panel.toggle}
        >
          <PanelRight size={16} />
        </button>
      </div>
    </div>
  )

  // ── Tom/ny samtale: header øverst, composer centreret midt på skærmen ──
  if (isEmpty) {
    return (
      <div className="chatview empty">
        {header}
        <div className="chat-empty">
          <h2>Hej.</h2>
          <p>Skriv hvad du arbejder på.</p>
          {composer}
        </div>
      </div>
    )
  }

  // ── Aktiv samtale ──
  return (
    <div className="chatview">
      {header}
      <div className="transcript" ref={transcriptRef} onScroll={onScroll}>
        {visibleMessages.map((m) => (
          <MessageRow
            key={m.id}
            role={m.role === 'user' ? 'user' : 'assistant'}
            blocks={m.content}
            density="compact"
            streaming={false}
            createdAt={m.created_at}
          />
        ))}
        {streaming && stream.blocks.length > 0 && (
          <MessageRow role="assistant" blocks={stream.blocks} density="compact" streaming />
        )}
        {/* Autonomt wakeup-run: token-stream live mens det kører. Når det er
            færdigt (status≠working) overtager serverens persisterede besked via
            refresh — så vi undgår dobbelt-render. */}
        {!streaming && bgActive && followState.status === 'working' && followState.blocks.length > 0 && (
          <MessageRow role="assistant" blocks={followState.blocks} density="compact" streaming />
        )}
      </div>

      <div className="composer-area">
        {/* Liveness fast lige over composer (ikke i transcript — den scrollede
            væk / sad i toppen ved ny chat). Vises kun når der faktisk sker noget. */}
        {(stream.status !== 'idle' || bgActive) && (
          <LivenessIndicator status={bgActive && stream.status !== 'working' ? 'working' : stream.status} elapsedMs={stream.elapsedMs} density="compact" workingStep={bgActive && stream.status !== 'working' ? 'vågner' : stream.workingStep} tokens={stream.usage.output} />
        )}
        <div className="composer-notices">
          {stream.status === 'interrupted' && <InterruptedBanner onResume={() => stream.continueFromPartial()} />}
          {stream.status === 'hung' && (
            <HangPrompt onResume={() => stream.continueFromPartial()} onAbort={() => void stream.abort()} />
          )}
          {stream.status === 'error' && stream.error && (
            <ErrorBanner message={stream.error.message} onDismiss={() => { /* ryddes ved næste send */ }} />
          )}
        </div>
        {!atBottom && (
          <button type="button" className="scroll-bottom-btn" onClick={scrollToBottom} aria-label="Til bund">
            <ArrowDown size={16} />
            {unread > 0 && <span className="scroll-badge">{unread} ny{unread > 1 ? 'e' : ''}</span>}
          </button>
        )}
        {queued && (
          <div className="queued-chip">
            <span className="queued-label">I kø</span>
            <span className="queued-text">{queued.text}</span>
            <button type="button" className="queued-cancel" onClick={() => setQueued(null)} aria-label="Fjern fra kø">×</button>
          </div>
        )}
        {composer}
      </div>
    </div>
  )
}
