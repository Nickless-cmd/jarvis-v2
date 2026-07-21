import { useEffect, useMemo, useReducer, useRef, useState } from 'react'
import { ArrowDown, PanelRight, Loader2 } from 'lucide-react'
import { streamReducer, initialStreamState } from '../lib/streamReducer'
import { useSessions } from '../hooks/useSessions'
import { useStream } from '../hooks/useStream'
import { useSettings } from '../hooks/useSettings'
import { usePanel } from '../hooks/usePanel'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { useVoiceConversation } from '../hooks/useVoiceConversation'
import { VoiceConversation } from '../components/chat/VoiceConversation'
import { usePermission } from '../hooks/usePermission'
import { useOnline } from '../hooks/useOnline'
import { readModelPrefs } from '../lib/composerPrefs'
import { getContextInfo, getContextUsage, getSessionMilestones, getActiveRuns, followRun, compactNow, warmSession } from '../lib/api'
import { markInteraction } from '../lib/presenceSignal'
import { PresenceDot } from '../components/shell/PresenceDot'
import { ConnectionPill } from '../components/shell/ConnectionPill'
import { CentralBadge } from '../components/shell/CentralBadge'
import { SystemHealth } from '../components/shell/SystemHealth'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'
import { ErrorCard } from '../components/feedback/ErrorCard'
import { GreetingHero } from '../components/chat/GreetingHero'
import { MessageRail, railLabel } from '../components/chat/MessageRail'

const NEAR_BOTTOM_PX = 120

/** Chat-mode. Ved tom/ny samtale: composer centreret midt på skærmen. Ved
 *  første besked oprettes session (hvis nødvendigt) og layoutet skifter — composer
 *  hopper ned i bunden, transcript fylder. */
export function ChatView({
  sessionId, userName = 'du', onOpenMarketplace, onOpenPrivacy,
}: {
  sessionId: string | null
  userName?: string
  onOpenMarketplace?: () => void
  onOpenPrivacy?: () => void
}) {
  const sessions = useSessions()
  const stream = useStream()
  const { settings, auth } = useSettings()
  const { permission } = usePermission()
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
  // Takeover-banner: når den ÅBNE session får cross-device-aktivitet (du tager
  // over fra mobilen) vises en lille notits "følger med live", så du ved
  // transcript'en opdaterer sig her — uden at hoppe ud og ind. Nulstilles når
  // aktiviteten stopper, så næste overtagelse vises igen.
  const [takeoverDismissed, setTakeoverDismissed] = useState(false)
  useEffect(() => {
    if (!bgActive) setTakeoverDismissed(false)
  }, [bgActive])
  // Follow-stream: token-stream et autonomt wakeup-runs svar live (i stedet for
  // at "dumpe" det ind når det er færdigt). Egen reducer fodret af /follow-SSE'en.
  const [followState, followDispatch] = useReducer(streamReducer, undefined, initialStreamState)
  const followCtrlRef = useRef<{ abort: () => void } | null>(null)

  // Debounced refresh (Bjørn 2026-06-29): vi havde FIRE stablede sessions.refresh()-
  // timere (700/2200ms efter eget done + 600/2000ms efter et fulgt run sluttede).
  // De ramte mergeServer i hurtig rækkefølge midt i bro/server/follow-vinduet og
  // forstørrede "3 svar lander samtidig"-racen. Nu coalescer alle persist-latency-
  // hentninger til ÉN refresh: hvert kald nulstiller en kort timer, så en byge af
  // triggere bliver præcis én GET. Dækker stadig sen persistering (sidste kald
  // vinder) men krymper race-vinduet markant.
  const debouncedRefreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const debouncedRefresh = (delayMs = 800) => {
    if (debouncedRefreshTimer.current) clearTimeout(debouncedRefreshTimer.current)
    debouncedRefreshTimer.current = setTimeout(() => {
      debouncedRefreshTimer.current = null
      void sessions.refresh()
    }, delayMs)
  }
  useEffect(() => () => {
    if (debouncedRefreshTimer.current) clearTimeout(debouncedRefreshTimer.current)
  }, [])

  // Context-ring (#9): hent autocompact-tærsklen én gang.
  useEffect(() => {
    if (!settings) return
    getContextInfo({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken })
      .then((r) => setCompactAt(r.compact_at))
      .catch(() => setCompactAt(0))
  }, [settings])

  // Context-ring: BACKEND-AUTORITATIVT fyld. Den gamle ring fodredes af per-tur stream-usage
  // (usage.input) der nulstilledes mellem ture og hoppede ulogisk (1 besked = 40%, næste =
  // tom — Bjørn 2026-06-23). Nu poller vi det ÆGTE transcript-estimat siden sidste compact —
  // præcis det tal autocompact selv måler mod. Persistent + harmonerer med compaction (vokser
  // mod loftet, falder når den fyrer). Re-poll ved session-skift + når stream-status skifter
  // (tur-grænser) + langsom interval.
  const [contextTokens, setContextTokens] = useState(0)
  const [overheadTokens, setOverheadTokens] = useState(0)
  const [compacting, setCompacting] = useState(false)
  useEffect(() => {
    if (!settings || !sessionId) { setContextTokens(0); setCompacting(false); return }
    let alive = true
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    const poll = () => getContextUsage(cfg, sessionId)
      .then((r) => { if (alive) { setContextTokens(r.tokens || 0); setOverheadTokens(r.overhead_tokens || 0); setCompacting(!!r.compacting) } })
      .catch(() => { /* behold sidste kendte ved netværksfejl */ })
    poll()
    const id = setInterval(poll, compacting ? 1200 : 6000)
    return () => { alive = false; clearInterval(id) }
  }, [settings, sessionId, stream.status, compacting])

  // Prewarm-on-return: når vinduet får fokus igen (bruger vender tilbage efter en
  // pause), varm sessionens DeepSeek-prefix så DEN FØRSTE besked rammer cachen i
  // stedet for cold prefill (~32k tokens = de oplevede >10s). Serveren throttler
  // 45s pr. session; best-effort/fire-and-forget. Session-åbning dækkes desuden
  // server-side (GET /chat/sessions/{id}). Se warmSession / session_prewarm.
  useEffect(() => {
    if (!settings || !sessionId) return
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    warmSession(cfg, sessionId)  // varm straks når en session vises
    const onFocus = () => { warmSession(cfg, sessionId) }
    window.addEventListener('focus', onFocus)
    return () => window.removeEventListener('focus', onFocus)
  }, [settings, sessionId])

  // Saved rail = MILEPÆLE (kapitler), ikke ét anker pr. besked (Bjørn 2026-06-23). Backend
  // segmenterer samtalen i titlede kapitler (cheap-lane, cached). Vi poller ved session-skift
  // + når en tur slutter. Indtil milepæle er klar (eller ved fejl) falder rail'en tilbage til
  // user-beskederne, så den aldrig forsvinder.
  const [milestones, setMilestones] = useState<{ anchor_id: string; title: string }[]>([])
  useEffect(() => {
    if (!settings || !sessionId) { setMilestones([]); return }
    let alive = true
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    getSessionMilestones(cfg, sessionId)
      .then((r) => { if (alive) setMilestones(r.milestones || []) })
      .catch(() => { /* behold sidste — fallback til user-beskeder nedenfor */ })
    return () => { alive = false }
  }, [settings, sessionId, stream.status === 'idle'])

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
          else if (stream.status !== 'working') {
            // ROBUSTHED (cross-device realtime, Bjørn 2026-06-20): et kort mobil-
            // svar-run kan starte+slutte mellem to ChatView-polls → vi misser
            // active-kanten (sidebar fangede den, men transcript'en opdaterede
            // aldrig). Pluk derfor ALTID den åbne sessions beskeder op når vi
            // ikke selv streamer. Billig GET; mergeServer dedup'er → ingen flicker.
            void sessions.refresh()
          }

          // HÄNG-DETEKTOR — NEUTRALISERET (Bjørn 2026-06-29: "mobil tog over /
          // desk hænger"). Vi aborterede før vores EGEN stadig-levende stream
          // når /active-runs missede sessionen 3 polls i træk (~4.5s). Men det
          // miss er et FALSK negativt under en langsom tool-runde: ping-loopet på
          // det detached event-loop sultes når tool'et arbejder synkront →
          // last_append_at fryser → live_run_ids dropper sessionen kortvarigt,
          // selvom runnet er i bedste velgående (server-autoritativt). Vores abort
          // dræbte så den levende stream → spinner hænger → takeover-banner, mens
          // mobilen (passiv follower) blev ved at vise broadcast'en. Et ÆGTE dødt
          // run dækkes nu udelukkende af stream-klientens 90s ping-watchdog
          // (streamClient PING_TIMEOUT_MS → onHung → synlig prompt). At tabe en
          // ægte abort er ufarligt (watchdog'en fanger den); en FALSK abort var
          // selve fejlen. Server-side er _LIVE_IDLE_S samtidig hævet 20→45s så
          // active-runs-misset bliver sjældnere overhovedet. Vi tæller stadig
          // miss'ene (observerbarhed/fremtidig brug) men handler ikke på dem.
          if (stream.status === 'working' && stream.workingSessionId === sessionId && !serverHasRun) {
            staleMisses += 1
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
      // skal stå, ikke vores rå live-stream. Én debounced refresh (var 2 stablede
      // timere) dækker persist-latency uden at forstørre bro/server-racen.
      debouncedRefresh(2000)
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

  // Follow-stream GENAKTIVERET (2026-06-19): den server-autoritative /live-
  // endpoint (server_authoritative_runs flag) er præcis translate-i-ENDPOINT-
  // redesignet kommentaren ventede på — frames læses fra run_event_log (translate
  // sker i den detached run-sti, IKKE i follow-endpointet), så den gamle
  // run-livscyklus-bug + abort-støj er væk. bgActive-guarden (stream.status !==
  // 'working') sikrer vi ALDRIG følger vores eget aktive send → ingen dobbelt-
  // render. followRun håndterer 204 (intet aktivt run) + abort rent.
  const FOLLOW_ENABLED = true
  useEffect(() => {
    if (!FOLLOW_ENABLED || !bgActive || !sessionId || !settings) return
    if (followCtrlRef.current) return // følger allerede
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    followCtrlRef.current = followRun(
      cfg, sessionId,
      (ev) => followDispatch(ev),
      () => {
        followCtrlRef.current = null
        // Et fulgt (cross-device/autonomt) run er afsluttet → hent den
        // persisterede + rensede besked ind i den ÅBNE transcript. Uden dette
        // står visningen tom indtil bruger skifter session (sessions.refresh i
        // pollet kan misse det sidste run hvis bgActive lige er droppet). Én
        // debounced refresh (var 2 stablede timere) dækker persist-latency.
        debouncedRefresh(2000)
      },
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

  // Re-pin til bund når transcript-containerens HØJDE ændrer sig (Bjørn 29. jun):
  // takeover-banneret ("anden enhed følger med") + liveness-indikatoren sidder UDENFOR
  // scroll-containeren, så når de dukker op krymper .transcript → nederste nye besked
  // falder under folden, og auto-scroll-effekten ovenfor (der kun lytter på blocks/atBottom)
  // fyrer ikke → det SER stille ud selvom streamen kører. ResizeObserver dækker ALLE
  // layout-ændringer generisk; respekterer at brugeren har scrollet op (kun ved atBottom).
  useEffect(() => {
    const el = transcriptRef.current
    if (!el || typeof ResizeObserver === 'undefined') return
    const ro = new ResizeObserver(() => {
      if (atBottom) el.scrollTop = el.scrollHeight
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [atBottom])

  const doSend = async (text: string, opts: ComposerSendOpts) => {
    markInteraction()  // device-presence: markér aktiv interaktion på denne enhed
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

  // Gensend: send en tidligere bruger-besked igen uden copy-paste. Bruger
  // aktuelle composer-præferencer (model/provider/permission).
  const resend = (text: string) => {
    const prefs = readModelPrefs()
    handleSend(text, {
      planMode: false,
      permission,
      attachments: [],
      model: prefs.model,
      providerChoice: prefs.providerChoice,
    })
  }

  const streaming = stream.status === 'working'

  // Kø: skriver man mens Jarvis streamer ELLER mens man er offline, lægges beskeden
  // i kø og sendes automatisk når turen er færdig / forbindelsen er tilbage (§14.1).
  // Deterministisk — ikke nudge.
  const online = useOnline()
  const [queued, setQueued] = useState<{ text: string; opts: ComposerSendOpts } | null>(null)
  // Manuel compaction (Claude-Code-stil /compact). Udløser samme motor NU. Valgfri fokus:
  // "/compact behold API-kontrakten vi lige lavede".
  const triggerManualCompact = async (focus: string) => {
    if (!settings || !sessionId) return
    setCompacting(true)  // optimistisk → liveness-linjen + composer-pausen tænder straks
    try {
      await compactNow({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }, sessionId, focus)
    } catch { /* pollen forliger tilstanden */ }
  }

  const handleSend = (text: string, opts: ComposerSendOpts) => {
    const t = text.trim()
    if (/^\/compact(\s|$)/i.test(t)) {
      const focus = t.replace(/^\/compact\s*/i, '').trim()
      void triggerManualCompact(focus)
      return  // kommando, ikke en chat-besked
    }
    if (streaming || !online) setQueued({ text, opts })
    else void doSend(text, opts)
  }
  useEffect(() => {
    // Flush når der hverken streames eller er offline (dækker både færdig-tur og reconnect).
    if (queued && stream.status !== 'working' && online) {
      const q = queued
      setQueued(null)
      void doSend(q.text, q.opts)
    }
  }, [stream.status, queued, online])

  const visibleMessages = sessions.messages.filter((m) => m.role === 'user' || m.role === 'assistant')

  // ÉN kilde pr. run (Bjørn 2026-06-29, "3 svar"): når et fulgt run's svar
  // ALLEREDE står i transcript'en (serveren har persisteret det, eller bro-kopien
  // er flettet ind) må vi IKKE samtidig rendere followState.blocks som en tredje
  // kopi. Sammenlign followState's normaliserede tekst med den sidste synlige
  // assistant-besked; matcher de, er det samme svar → undertryk follow-renderen.
  const followText = followState.blocks
    .map((b) => (b.type === 'text' ? b.text : b.type === 'thinking' ? '' : '')).join('')
    .replace(/\s+/g, ' ').trim()
  const lastVisibleAsst = [...visibleMessages].reverse().find((m) => m.role === 'assistant')
  const lastVisibleAsstText = lastVisibleAsst
    ? (Array.isArray(lastVisibleAsst.content)
        ? lastVisibleAsst.content.map((b) => (b.type === 'text' ? b.text : '')).join('')
        : String(lastVisibleAsst.content || '')
      ).replace(/\s+/g, ' ').trim()
    : ''
  const followAlreadyInTranscript =
    followText.length > 0 && lastVisibleAsstText.length > 0 &&
    (lastVisibleAsstText === followText || lastVisibleAsstText.startsWith(followText) || followText.startsWith(lastVisibleAsstText))
  // Rail-ankre: MILEPÆLE (kapitler) når de findes (≥2 der matcher synlige beskeder), ellers
  // fallback til user-beskederne så rail'en aldrig er tom mens milepæle genereres.
  const railAnchors = useMemo(() => {
    const ids = new Set(visibleMessages.map((m) => m.id))
    const fromMilestones = milestones
      .filter((m) => ids.has(m.anchor_id))
      .map((m) => ({ id: m.anchor_id, label: m.title }))
    if (fromMilestones.length >= 2) return fromMilestones
    return visibleMessages.filter((m) => m.role === 'user').map((m) => ({ id: m.id, label: railLabel(m.content) }))
  }, [milestones, visibleMessages])
  const isEmpty =
    !sessionId ||
    (visibleMessages.length === 0 && stream.status === 'idle' && stream.blocks.length === 0 && !queued && !bgActive)

  const ensureSessionId = async () => {
    if (sessionId) return sessionId
    const created = await sessions.create('Ny samtale')
    return created.id
  }

  // Samtale-mode (Trin 2): hook + overlay. sendMessage = resend (sender med composer-prefs).
  const voiceConfig = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const voice = useVoiceConversation(voiceConfig, {
    status: stream.status,
    blocks: stream.blocks,
    sendMessage: resend,
  })

  const composer = (
    <>
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
        overheadTokens={overheadTokens}
        compactAt={compactAt}
        compacting={compacting}
        onManualCompact={() => void triggerManualCompact('')}
        isOwner={auth?.role === 'owner'}
        onOpenPrivacy={onOpenPrivacy}
      />
      <VoiceConversation
        active={voice.active}
        state={voice.state}
        mode={voice.mode}
        supported={voice.supported}
        lastProvider={voice.lastProvider}
        setMode={voice.setMode}
        startListening={voice.startListening}
        stopListening={voice.stopListening}
        exit={voice.exit}
      />
    </>
  )

  const activeSession = sessions.sessions.find((s) => s.id === sessionId)
  const chatTitle = activeSession?.title || (isEmpty ? 'Ny samtale' : 'Samtale')
  const header = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={bgActive && stream.status !== 'working' ? 'working' : stream.status} /> <span className="chat-title">{chatTitle}</span>
      </div>
      <div className="chatview-head-right">
        <SystemHealth errors={stream.canonicalErrors} />
        {settings && (
          <CentralBadge config={{ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }} isOwner={auth?.role === 'owner'} />
        )}
        {settings && (
          <ConnectionPill config={{ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }} />
        )}
        {voice.supported && (
          <button
            type="button"
            className="panel-toggle"
            aria-label="Samtale-mode"
            title="Samtale med Jarvis (stemme)"
            onClick={voice.enter}
          >
            🎙️
          </button>
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
          <GreetingHero
            config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
            userName={userName}
            onOpenMarketplace={() => onOpenMarketplace?.()}
            onSuggest={(text) => resend(text)}
          >
            {composer}
          </GreetingHero>
        </div>
      </div>
    )
  }

  // ── Aktiv samtale ──
  const showTakeover = bgActive && stream.status !== 'working' && !takeoverDismissed
  return (
    <div className="chatview">
      {header}
      {showTakeover && (
        <div className="takeover-banner" role="status">
          <span className="takeover-text">📱→🖥 Aktiv på en anden enhed — følger med her live</span>
          <button
            type="button"
            className="takeover-dismiss"
            aria-label="Skjul"
            onClick={() => setTakeoverDismissed(true)}
          >
            ×
          </button>
        </div>
      )}
      <div className="transcript-wrap">
      <MessageRail
        containerRef={transcriptRef}
        anchors={railAnchors}
      />
      <div className="transcript" ref={transcriptRef} onScroll={onScroll}>
        {visibleMessages.map((m) => (
          <div key={m.id} data-rail-id={m.id} className="msg-block">
          <MessageRow
            role={m.role === 'user' ? 'user' : 'assistant'}
            blocks={m.content}
            density="compact"
            streaming={false}
            createdAt={m.created_at}
            onResend={m.role === 'user' ? resend : undefined}
            config={settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined}
          />
          </div>
        ))}
        {streaming && stream.blocks.length > 0 && (
          <MessageRow role="assistant" blocks={stream.blocks} density="compact" streaming />
        )}
        {/* Autonomt wakeup-run: token-stream live mens det kører. Når det er
            færdigt (status≠working) overtager serverens persisterede besked via
            refresh — så vi undgår dobbelt-render. ÉN kilde pr. run: undertryk
            follow-renderen hvis svaret allerede står i transcript'en (server/bro). */}
        {!streaming && bgActive && followState.status === 'working' && followState.blocks.length > 0 && !followAlreadyInTranscript && (
          <MessageRow role="assistant" blocks={followState.blocks} density="compact" streaming />
        )}
      </div>
      </div>

      <div className="composer-area">
        {/* Liveness fast lige over composer (ikke i transcript — den scrollede
            væk / sad i toppen ved ny chat). Vises kun når der faktisk sker noget. */}
        {(stream.status !== 'idle' || bgActive) && (
          <LivenessIndicator status={bgActive && stream.status !== 'working' ? 'working' : stream.status} elapsedMs={stream.elapsedMs} density="compact" workingStep={bgActive && stream.status !== 'working' ? 'vågner' : stream.workingStep} tokens={stream.usage.output} />
        )}
        {/* Compaction-pause (som Claude Code): mens sessionen komprimeres pauses composeren
            og en linje viser status. En besked skrevet imens sendes automatisk bagefter. */}
        {compacting && (
          <div className="liveness liveness-compact is-working" role="status" aria-live="polite">
            <Loader2 size={14} className="spin" />
            <span className="liveness-label">Komprimerer kontekst — sessionen er pauset et øjeblik…</span>
          </div>
        )}
        <div className="composer-notices">
          {stream.status === 'interrupted' && <InterruptedBanner onResume={() => stream.continueFromPartial()} />}
          {stream.status === 'hung' && (
            <HangPrompt onResume={() => stream.continueFromPartial()} onAbort={() => void stream.abort()} />
          )}
          {stream.status === 'reconnecting' && (
            <div className="banner banner-reconnecting" role="status">
              <span className="banner-message">Forbindelsen røg — genforbinder…</span>
              <button type="button" className="banner-dismiss" aria-label="afbryd" onClick={() => void stream.abort()}>×</button>
            </div>
          )}
          {stream.status === 'error' && stream.canonicalError && stream.canonicalError.kind ? (
            // Fase 2: rig ErrorCard når fejlen har en kanonisk kind; ellers fallback nedenfor.
            <ErrorCard
              error={stream.canonicalError}
              onDismiss={() => stream.clearError()}
              onRetry={stream.canonicalError.retryable ? () => {
                const last = [...visibleMessages].reverse().find((m) => m.role === 'user')
                const text = Array.isArray(last?.content)
                  ? last!.content.map((b) => (b.type === 'text' ? b.text : '')).join('')
                  : ''
                stream.clearError()
                if (text.trim()) resend(text)
              } : undefined}
            />
          ) : stream.status === 'error' && stream.streamError && (
            <ErrorBanner
              message={stream.streamError.message}
              severity={stream.streamError.severity}
              fixHint={stream.streamError.fixHint}
              onDismiss={() => stream.clearError()}
              onRetry={stream.streamError.retryable ? () => {
                const last = [...visibleMessages].reverse().find((m) => m.role === 'user')
                const text = Array.isArray(last?.content)
                  ? last!.content.map((b) => (b.type === 'text' ? b.text : '')).join('')
                  : ''
                stream.clearError()
                if (text.trim()) resend(text)
              } : undefined}
            />
          )}
        </div>
        {!atBottom && (
          <button type="button" className="scroll-bottom-btn" onClick={scrollToBottom} aria-label="Til bund">
            <ArrowDown size={16} />
            {unread > 0 && <span className="scroll-badge">{unread} ny{unread > 1 ? 'e' : ''}</span>}
          </button>
        )}
        {queued && (
          <div className={`queued-chip ${!online ? 'is-offline' : ''}`}>
            <span className="queued-label">{!online ? 'Offline — sendes når forbindelsen er tilbage' : 'I kø'}</span>
            <span className="queued-text">{queued.text}</span>
            <button type="button" className="queued-cancel" onClick={() => setQueued(null)} aria-label="Fjern fra kø">×</button>
          </div>
        )}
        {composer}
      </div>
    </div>
  )
}
