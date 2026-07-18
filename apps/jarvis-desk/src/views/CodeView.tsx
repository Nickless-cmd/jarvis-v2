import { useEffect, useReducer, useRef, useState } from 'react'
import { FolderTree, PanelRight, Lock, ShieldCheck, FolderOpen, ArrowDown, Gauge } from 'lucide-react'
import { useStream } from '../hooks/useStream'
import { usePermission } from '../hooks/usePermission'
import { useSettings } from '../hooks/useSettings'
import { useSessions } from '../hooks/useSessions'
import { usePanel } from '../hooks/usePanel'
import { readModelPrefs } from '../lib/composerPrefs'
import { MessageRow } from '../components/rich/MessageRow'
import { Composer, type ComposerSendOpts } from '../components/shell/Composer'
import { LivenessIndicator } from '../components/feedback/LivenessIndicator'
import { InterruptedBanner } from '../components/feedback/InterruptedBanner'
import { HangPrompt } from '../components/feedback/HangPrompt'
import { ErrorBanner } from '../components/feedback/ErrorBanner'
import { ApprovalCard } from '../components/rich/ApprovalCard'
import { PresenceDot } from '../components/shell/PresenceDot'
import { ConnectionPill } from '../components/shell/ConnectionPill'
import { GitChip } from '../components/shell/GitChip'
import { CodePanel } from '../components/panel/CodePanel'
import { EnvironmentPanel } from '../components/code/EnvironmentPanel'
import { CentralBadge } from '../components/shell/CentralBadge'
import { SystemHealth } from '../components/shell/SystemHealth'
import { OperatorPanel } from '../components/code/OperatorPanel'
import { MessageRail, railLabel } from '../components/chat/MessageRail'
import { GreetingHero } from '../components/chat/GreetingHero'
import { useResizableWidth } from '../components/panel/useResizableWidth'
import { onHighlight } from '../lib/fileTreeHighlight'
import { getWorkspaceTrust, setWorkspaceTrust, getContextInfo, getContextUsage, compactNow, getActiveRuns, followRun } from '../lib/api'
import { streamReducer, initialStreamState } from '../lib/streamReducer'

// Navngivne server-roots (matcher backend _allowed_roots). Owner: hele kodebasen
// (repo) + runtime-home (~/.jarvis-v2/) + eget workspace. Member: KUN eget workspace.
const OWNER_ROOTS = ['repo', 'jarvis-v2', 'workspace'] as const
const MEMBER_ROOTS = ['workspace'] as const

// Pæne labels til root-vælgeren.
const ROOT_LABELS: Record<string, string> = {
  repo: 'Kodebase', 'jarvis-v2': 'Runtime (~/.jarvis-v2)', workspace: 'Mit workspace',
}

type WsKind = 'container' | 'workstation'
type Role = 'owner' | 'member' | 'guest'

/** Native mappe-vælger (Electron). Returnerer valgt sti eller null udenfor app'en. */
async function pickFolder(): Promise<string | null> {
  const bridge = (window as unknown as { jarvisDesk?: { pickFolder?: () => Promise<string | null> } }).jarvisDesk
  if (!bridge?.pickFolder) return null
  return bridge.pickFolder()
}

/** Code mode: Jarvis koder i et valgt workspace — server (repo/dit workspace) eller
 *  en mappe på din egen computer (via operator-bridgen). Stream i midten; foldbare
 *  fil-træ- og preview-paneler i højre. Layout spejler chat (centreret velkomst). */
export function CodeView({
  sessionId, userName, role = 'owner', onOpenMarketplace, onOpenPrivacy,
}: { sessionId: string | null; userName?: string; role?: Role; onOpenMarketplace?: () => void; onOpenPrivacy?: () => void }) {
  const stream = useStream()
  const { permission } = usePermission()
  const { settings } = useSettings()
  const sessions = useSessions()
  const panel = usePanel()
  const isOwner = role === 'owner'
  const serverRoots = isOwner ? OWNER_ROOTS : MEMBER_ROOTS
  // Toggle-label: server-side vs egen computer. Det konkrete root (Kodebase/
  // Runtime/Mit workspace) vises i selve root-vælgeren ved siden af.
  const serverLabel = 'Server'

  // Husk sidste workspace-valg på tværs af genstart (kind/root/sti). Trust ligger
  // server-side; uden dette mistede man bare SELEKTIONEN og skulle re-vælge mappe.
  const savedWs = (() => {
    try { return JSON.parse(localStorage.getItem('jarvis-desk:code-ws') || '{}') } catch { return {} }
  })() as { kind?: WsKind; root?: string; wsPath?: string }

  const [kind, setKind] = useState<WsKind>(savedWs.kind === 'workstation' ? 'workstation' : 'container')
  const [root, setRoot] = useState<string>(savedWs.root && serverRoots.includes(savedWs.root as never) ? savedWs.root : serverRoots[0])
  const [wsPath, setWsPath] = useState<string>(savedWs.wsPath || '') // valgt workstation-mappe
  const [filesOpen, setFilesOpen] = useState(false) // fil-træ foldet ind fra start
  const [highlightPath, setHighlightPath] = useState<string>('') // Jarvis-styret highlight
  const [trusted, setTrusted] = useState<boolean | null>(null)
  const [compactAt, setCompactAt] = useState(0)
  // Context-ring: BACKEND-AUTORITATIVT transcript-fyld siden sidste compact (samme som chat).
  // FØR (bug): ringen blev fodret af stream.usage.input+cacheHit = HELE prompten INKL.
  // system-prompten → "skøjtede" og talte system-prompten med. Nu poller vi det ægte
  // transcript-tal (falder når compaction fyrer) + overhead til tooltip + compacting-status.
  const [contextTokens, setContextTokens] = useState(0)
  const [overheadTokens, setOverheadTokens] = useState(0)
  const [compacting, setCompacting] = useState(false)
  const [gitRefresh, setGitRefresh] = useState(0) // bumpes når et run slutter → GitChip gen-henter
  // Miljø-felt: toggle som panel-ikonerne. null = auto (vis ved fuld skærm / bredt
  // vindue, skjul når smalt så det ikke dækker chatten). Bruger kan overstyre.
  const [envManual, setEnvManual] = useState<boolean | null>(null)
  const [winW, setWinW] = useState<number>(typeof window !== 'undefined' ? window.innerWidth : 1920)
  useEffect(() => {
    const onResize = () => setWinW(window.innerWidth)
    window.addEventListener('resize', onResize)
    return () => window.removeEventListener('resize', onResize)
  }, [])
  const envWide = winW >= 1180 // proxy for "fuld skærm / bredt nok til ikke at overlappe"
  const envOpen = (envManual ?? envWide)

  // Dependency-gate: er git til stede på maskinen? (Electron deps-bro; web → antag ja.)
  const [gitMissing, setGitMissing] = useState(false)
  const [installingTool, setInstallingTool] = useState('')
  const depsBridge = () =>
    (window as unknown as { jarvisDesk?: { deps?: {
      detect: () => Promise<{ tool: string; present: boolean }[]>
      install: (t: string) => Promise<{ ok: boolean }>
    } } }).jarvisDesk?.deps
  useEffect(() => {
    const d = depsBridge()
    if (!d) return
    let cancelled = false
    void d.detect().then((tools) => {
      const git = tools.find((t) => t.tool === 'git')
      if (!cancelled && git) setGitMissing(!git.present)
    }).catch(() => { /* ignore */ })
    return () => { cancelled = true }
  }, [])
  const onInstallTool = (tool: string) => {
    const d = depsBridge()
    if (!d || installingTool) return
    setInstallingTool(tool)
    void d.install(tool).then((r) => { if (r.ok && tool === 'git') setGitMissing(false) })
      .finally(() => setInstallingTool(''))
  }

  // Session-akkumulering til miljø-feltet: tokens + tool-kald + tool-liste SAMLET
  // over HELE sessionen (ikke pr. run), så man kan se alt der er lavet (Codex-stil).
  // Cross-device live-state (effekter wires længere nede): bruges allerede her i
  // miljø-felt-beregningen, så deklarationen skal stå før den.
  const [bgActive, setBgActive] = useState(false)
  const [followState, followDispatch] = useReducer(streamReducer, undefined, initialStreamState)
  const followCtrlRef = useRef<{ abort: () => void } | null>(null)

  // Hjælper: indlæs gemte session-stats fra localStorage.
  function _loadStats(sid: string | null): { tokens: number; toolCalls: number; tools: { name: string; input: Record<string, unknown> }[] } {
    if (!sid) return { tokens: 0, toolCalls: 0, tools: [] }
    try {
      const raw = localStorage.getItem(`jarvis-desk:session-stats:${sid}`)
      return raw ? JSON.parse(raw) : { tokens: 0, toolCalls: 0, tools: [] }
    } catch { return { tokens: 0, toolCalls: 0, tools: [] } }
  }
  // Hjælper: gem session-stats til localStorage.
  function _saveStats(sid: string, tokens: number, toolCalls: number, tools: { name: string; input: Record<string, unknown> }[]) {
    try { localStorage.setItem(`jarvis-desk:session-stats:${sid}`, JSON.stringify({ tokens, toolCalls, tools })) }
    catch { /* localStorage utilgængelig — ignorér */ }
  }

  // Foldes når et run slutter (working → ikke-working); nulstilles ved session-skift.
  // PERSISTENT: gemmes i localStorage pr. sessionId, så miljø-feltets historik
  // overlever app-genstart. Loades ved mount + session-skift; skrives ved hver opdatering.
  const initStats = useRef(_loadStats(sessionId))
  const [sessTokens, setSessTokens] = useState(initStats.current.tokens)
  const [sessToolCalls, setSessToolCalls] = useState(initStats.current.toolCalls)
  const [sessTools, setSessTools] = useState<{ name: string; input: Record<string, unknown> }[]>(initStats.current.tools)
  const prevStatusRef = useRef(stream.status)
  // Per-run dedup-vagt for reconcile (D1, 29. jun): uden den kan en re-render mens
  // status stadig er 'done' (eller onComplete's message_stop-gendispatch) reconcile
  // SAMME assistant-svar to gange → dublet i transcript. ChatView har haft denne
  // vagt; code-mode manglede den.
  const reconciledForRun = useRef<string | null>(null)
  // Anonym ref til at gemme FORRIGE sessionsId (så vi kan gemme dens stats ved skift).
  const prevSessionRef = useRef<string | null>(sessionId)
  useEffect(() => {
    const prev = prevSessionRef.current
    prevSessionRef.current = sessionId
    if (prev && prev !== sessionId) {
      // Gem forrige sessions stats inden vi rydder.
      _saveStats(prev, sessTokens, sessToolCalls, sessTools)
    }
    const loaded = _loadStats(sessionId)
    setSessTokens(loaded.tokens)
    setSessToolCalls(loaded.toolCalls)
    setSessTools(loaded.tools)
    prevStatusRef.current = stream.status
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId])
  // Persistér session-stats ved enhver ændring (akkumulerede tokens/tools).
  const persistTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  useEffect(() => {
    if (!sessionId) return
    // Debounced: skriv til localStorage max 1 gang pr. 500ms for at undgå
    // skrive-storm under en tool-tung tur.
    if (persistTimer.current) clearTimeout(persistTimer.current)
    persistTimer.current = setTimeout(() => _saveStats(sessionId, sessTokens, sessToolCalls, sessTools), 500)
    return () => { if (persistTimer.current) clearTimeout(persistTimer.current) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessTokens, sessToolCalls, sessTools])
  useEffect(() => {
    const prev = prevStatusRef.current
    prevStatusRef.current = stream.status
    if (prev === 'working' && stream.status !== 'working') {
      const tb = stream.blocks
        .filter((b) => b.type === 'tool_use')
        .map((b) => ({ name: (b as { name?: string }).name || '', input: ((b as { input?: Record<string, unknown> }).input) || {} }))
      setSessTokens((t) => t + (stream.usage.output || 0))
      setSessToolCalls((c) => c + tb.length)
      if (tb.length) setSessTools((prevT) => [...prevT, ...tb].slice(-50))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.status])
  // CROSS-DEVICE tool-akkumulator (mobil-run): message_start NULSTILLER
  // followState.blocks pr. agentisk tur, så en snapshot ved run-slut ser kun
  // SIDSTE turs blocks → tool-ture tabes. Vi tæller derfor tool_use på
  // EVENT-niveau (i follow-callbacken nedenfor), uafhængigt af React-batching og
  // blocks-reset. bgTools vises live i miljø-feltet og foldes ind i session-
  // totalerne når runnet er HELT slut (bgActive true→false).
  const [bgTools, setBgTools] = useState<{ name: string; input: Record<string, unknown> }[]>([])
  // Fold cross-device tokens ind pr. tur (followState.usage.output nulstilles ved
  // ny tur, så kumulativt = sessTokens + nuværende turs output). Tools håndteres
  // af bgTools-akkumulatoren, IKKE her.
  const prevFollowRef = useRef(followState.status)
  useEffect(() => {
    const prev = prevFollowRef.current
    prevFollowRef.current = followState.status
    if (prev === 'working' && followState.status !== 'working') {
      setSessTokens((t) => t + (followState.usage.output || 0))
      setGitRefresh((n) => n + 1) // git/diff kan have ændret sig via mobil-runnet
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [followState.status])
  // Når et cross-device run er HELT slut (latch udløbet): fold de akkumulerede
  // tools ind i session-historikken og nulstil akkumulatoren til næste run.
  const prevBgActiveRef = useRef(bgActive)
  useEffect(() => {
    const was = prevBgActiveRef.current
    prevBgActiveRef.current = bgActive
    if (was && !bgActive && bgTools.length) {
      setSessToolCalls((c) => c + bgTools.length)
      setSessTools((prevT) => [...prevT, ...bgTools].slice(-50))
      setBgTools([])
    } else if (!was && bgActive) {
      setBgTools([]) // nyt run → frisk akkumulator
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bgActive])
  // Live (igangværende run) lægges oven i session-totalerne så tallene er "live".
  // Både vores eget lokale run OG et fulgt cross-device run (mobil).
  const bgWorking = bgActive && stream.status !== 'working'
  // Lokale tools fra vores egen stream (kun nuværende tur — lokal sti folder pr. tur).
  const localLiveTools = stream.status === 'working'
    ? stream.blocks.filter((b) => b.type === 'tool_use')
        .map((b) => ({ name: (b as { name?: string }).name || '', input: ((b as { input?: Record<string, unknown> }).input) || {} }))
    : []
  // Cross-device tools = event-akkumulatoren (alle ture), vist mens runnet kører.
  const crossLiveTools = bgActive ? bgTools : []
  const liveUsageOut = stream.status === 'working' ? (stream.usage.output || 0) : (bgWorking ? (followState.usage.output || 0) : 0)
  const envTotalTokens = sessTokens + liveUsageOut
  const envTotalToolCalls = sessToolCalls + localLiveTools.length + crossLiveTools.length
  const envTools = [...sessTools, ...localLiveTools, ...crossLiveTools]
  // Trækbar bredde på hele fil-/preview-panelet (mod venstre). Bredere default
  // end før (380→460) så preview-ruden ikke er knald-smal.
  const codePanelW = useResizableWidth({
    initial: 560, min: 300, max: 1000, side: 'left', storageKey: 'jarvis-desk:code-panel-w2',
  })
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined

  // Context-ring: hent autocompact-tærsklen (samme som chat).
  useEffect(() => {
    if (!config) return
    getContextInfo(config).then((r) => setCompactAt(r.compact_at)).catch(() => setCompactAt(0))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.apiBaseUrl, config?.authToken])

  // Backend-autoritativt transcript-fyld + overhead + compacting-status (samme som ChatView).
  useEffect(() => {
    if (!config || !sessionId) { setContextTokens(0); setOverheadTokens(0); setCompacting(false); return }
    let alive = true
    const poll = () => getContextUsage(config, sessionId)
      .then((r) => { if (alive) { setContextTokens(r.tokens || 0); setOverheadTokens(r.overhead_tokens || 0); setCompacting(!!r.compacting) } })
      .catch(() => { /* behold sidste kendte */ })
    poll()
    const id = setInterval(poll, compacting ? 1200 : 6000)
    return () => { alive = false; clearInterval(id) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config?.apiBaseUrl, config?.authToken, sessionId, stream.status, compacting])

  // Manuel compaction (Claude-Code /compact). Udløser samme motor NU.
  const triggerManualCompact = async (focus: string) => {
    if (!config || !sessionId) return
    setCompacting(true)  // optimistisk → liveness-pausen tænder straks
    try { await compactNow(config, sessionId, focus) } catch { /* pollen forliger */ }
  }

  // Opfang /compact FØR den sendes som en normal besked (ellers "tænker" modellen bare).
  const handleSend = (text: string, opts: ComposerSendOpts) => {
    const t = text.trim()
    if (/^\/compact(\s|$)/i.test(t)) {
      void triggerManualCompact(t.replace(/^\/compact\s*/i, '').trim())
      return
    }
    void doSend(text, opts)
  }

  // Persistér workspace-valget ved enhver ændring.
  useEffect(() => {
    try {
      localStorage.setItem('jarvis-desk:code-ws', JSON.stringify({ kind, root, wsPath }))
    } catch { /* localStorage utilgængelig — ignorér */ }
  }, [kind, root, wsPath])

  // Jarvis-styret highlight (open_ui_panel panel="file_tree"): vis server-repoet
  // (owner) + åbn fil-træet + scroll-til filen. Stien er repo-relativ.
  // Jarvis-styret highlight (open_ui_panel panel="file_tree"):
  // scope='repo' (default): highlight i serverens repo.
  // scope='workstation': highlight i brugerens lokale workspace.
  // Hvis intet workspace er valgt, forsøg at bede brugeren valge via pickFolder-bridge.
  useEffect(() => onHighlight((p, scope) => {
    if (scope === 'workstation') {
      setKind('workstation')
      if (wsPath) {
        setFilesOpen(true)
        setHighlightPath(' ')
        requestAnimationFrame(() => setHighlightPath(p))
      } else {
        // Intet workspace valgt — forsøg pickFolder
        const bridge = (window as unknown as { jarvisDesk?: { pickFolder?: () => Promise<string | null> } }).jarvisDesk
        if (bridge?.pickFolder) {
          bridge.pickFolder().then((folder) => {
            if (folder) {
              setWsPath(folder)
              setFilesOpen(true)
              setHighlightPath(' ')
              requestAnimationFrame(() => setHighlightPath(p))
            }
          })
        }
      }
    } else {
      // scope='repo' (default): nuvarende adfaerd
      setKind('container')
      if (isOwner) setRoot('repo')
      setFilesOpen(true)
      setHighlightPath(' ')
      requestAnimationFrame(() => setHighlightPath(p))
    }
  }), [isOwner])
  const effRoot = kind === 'container' ? root : wsPath
  const ready = !!effRoot // workstation kræver at en mappe er valgt

  // Autoscroll + scroll-til-bund-pil (som chat).
  const transcriptRef = useRef<HTMLDivElement>(null)
  const [atBottom, setAtBottom] = useState(true)
  const [unread, setUnread] = useState(0)
  const NEAR_BOTTOM_PX = 120

  // ── Cross-device live (porteret 1:1 fra ChatView) ──────────────────────────
  // Code mode skal lyse op PRÆCIS som Chat mode når mobilen tager over: header-
  // spinner, token-tæller og live-transcript i SELVE viewet — ikke en popup ved
  // siden af. Mekanik: poll active-runs (6s-latch så korte runs ikke forsvinder
  // mellem to polls) → bgActive; følg /live → followState (token-stream); hent den
  // persisterede besked ind via sessions.refresh under+efter runnet.
  // (bgActive/followState/followCtrlRef deklareres tidligere — miljø-feltet
  // bruger dem allerede.)
  const [takeoverDismissed, setTakeoverDismissed] = useState(false)
  useEffect(() => { if (!bgActive) setTakeoverDismissed(false) }, [bgActive])
  // Egen sekund-tæller til liveness-linjen: stream.elapsedMs er 0 ved et cross-
  // device run (vi streamer ikke selv), så den ville stå på 00:00. Tæl fra da
  // bgActive blev sat.
  const [bgElapsedMs, setBgElapsedMs] = useState(0)
  const bgStartRef = useRef(0)
  useEffect(() => {
    if (!bgActive) { setBgElapsedMs(0); return }
    bgStartRef.current = Date.now()
    setBgElapsedMs(0)
    const t = setInterval(() => setBgElapsedMs(Date.now() - bgStartRef.current), 1000)
    return () => clearInterval(t)
  }, [bgActive])
  useEffect(() => {
    if (!settings || !sessionId) { setBgActive(false); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    let cooldown = 0
    let bgUntil = 0
    const tick = () => {
      void getActiveRuns(cfg)
        .then((ids) => {
          if (cancelled) return
          const serverHasRun = ids.includes(sessionId)
          const active = serverHasRun && stream.status !== 'working'
          if (active) bgUntil = Date.now() + 6000
          setBgActive(active || Date.now() < bgUntil)
          if (active) { cooldown = 3; void sessions.refresh() }
          else if (cooldown > 0) { cooldown -= 1; void sessions.refresh() }
          else if (stream.status !== 'working') { void sessions.refresh() }
        })
        .catch(() => { /* behold sidste — ingen flicker */ })
    }
    tick()
    const id = setInterval(tick, 1500)
    return () => { cancelled = true; clearInterval(id) }
  }, [settings, sessionId, stream.status])
  useEffect(() => {
    if (!bgActive || !sessionId || !settings) return
    if (followCtrlRef.current) return
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    followCtrlRef.current = followRun(
      cfg, sessionId,
      (ev) => {
        // Akkumulér tool_use på EVENT-niveau (uafhængigt af blocks-reset pr. tur)
        // så miljø-feltet fanger ALLE tool-kald i et agentisk mobil-run.
        if (ev && ev.type === 'content_block_start') {
          const cb = (ev as { content_block?: { type?: string; name?: string; input?: Record<string, unknown> } }).content_block
          if (cb && cb.type === 'tool_use') {
            setBgTools((prev) => [...prev, { name: cb.name || '', input: cb.input || {} }].slice(-50))
          }
        }
        followDispatch(ev)
      },
      () => {
        followCtrlRef.current = null
        setTimeout(() => { void sessions.refresh() }, 600)
        setTimeout(() => { void sessions.refresh() }, 2000)
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

  useEffect(() => { if (sessionId) sessions.select(sessionId) }, [sessionId])

  // PERSISTENT storyboard (Bjørn 2. jul: "hver gang appen genstartes så nulstilles
  // historikken"): chat lander bevidst på greeting-skærm ved opstart (activeId=null),
  // men code mode er et vedvarende storyboard — det skal GENOPTAGE sidste kode-session.
  // Vi husker sidste kode-sessions-id i sin EGEN nøgle (rører ikke chats greeting-
  // adfærd) og gen-vælger den når session-listen er loaded ved mount. Stats/tool-
  // historik hænger på sessionId, så det følger med tilbage.
  const LAST_CODE_KEY = 'jarvis-desk:lastCodeSession'
  useEffect(() => {
    if (sessionId) { try { localStorage.setItem(LAST_CODE_KEY, sessionId) } catch { /* ignore */ } }
  }, [sessionId])
  const restoredCode = useRef(false)
  useEffect(() => {
    if (restoredCode.current || sessionId) return
    if (sessions.sessions.length === 0) return // liste endnu ikke loaded
    let last: string | null = null
    try { last = localStorage.getItem(LAST_CODE_KEY) } catch { /* ignore */ }
    if (last && sessions.sessions.some((s) => s.id === last)) {
      restoredCode.current = true
      sessions.select(last)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessions.sessions, sessionId])

  // Reconcile assistant-svar ind i transcript når et run slutter (som chat).
  useEffect(() => {
    if (stream.status === 'done' && stream.blocks.length > 0
        && reconciledForRun.current !== stream.activeRunId) {
      reconciledForRun.current = stream.activeRunId
      sessions.reconcile({
        id: `a-${stream.activeRunId ?? Date.now()}`,
        role: 'assistant',
        content: stream.blocks,
        created_at: new Date().toISOString(),
        parent_id: null,
      })
      setGitRefresh((k) => k + 1) // Jarvis kan have ændret filer → opdater git-chip
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.status])

  // Trusted-folder gate: tjek om det valgte workspace er betroet (skrive/exec).
  useEffect(() => {
    if (!config || !ready) { setTrusted(ready ? null : true); return }
    let cancelled = false
    setTrusted(null)
    getWorkspaceTrust(config, kind, effRoot)
      .then((t) => { if (!cancelled) setTrusted(t) })
      .catch(() => { if (!cancelled) setTrusted(false) })
    return () => { cancelled = true }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [kind, effRoot, config?.apiBaseUrl, config?.authToken])

  const trustFolder = async () => {
    if (!config || !ready) return
    try {
      const t = await setWorkspaceTrust(config, kind, effRoot, true)
      setTrusted(t)
    } catch { /* lad banneret blive — brugeren kan prøve igen */ }
  }

  const choosePath = async () => {
    const p = await pickFolder()
    if (p) { setKind('workstation'); setWsPath(p) }
  }

  const doSend = async (text: string, opts: ComposerSendOpts) => {
    if (!ready) return
    let sid = sessionId
    if (!sid) sid = (await sessions.create('Kode-session')).id
    const message = text.trim() || 'Vedhæftet'
    sessions.appendOptimistic({
      id: `u-${Date.now()}`,
      role: 'user',
      content: [{ type: 'text', text: message }],
      created_at: new Date().toISOString(),
      parent_id: null,
    })
    stream.send(message, {
      sessionId: sid,
      approvalMode: opts.permission,
      attachmentIds: opts.attachments.map((a) => a.id),
      mode: 'code',
      workspaceKind: kind,
      workspaceRoot: effRoot,
      model: opts.model,
      providerChoice: opts.providerChoice,
    })
  }

  // Auto-continue: efter et godkendt mode/permission-skift gen-sendes den
  // oprindelige besked her, så Jarvis fortsætter sømløst i code mode.
  //
  // KRITISK timing-gate (2026-06-17): re-send'et MÅ ikke fyre mens det
  // oprindelige chat-run stadig kører. Kortet kan klikkes før Jarvis når
  // message_stop; fyrer vi da, POSTer vi et nyt run i SAMME session mens det
  // gamle stadig er aktivt server-side → visible_runs' same-session-guard
  // midway-nudge'r det nye run (yielder intet) → SSE lukker uden message_stop
  // → klienten viser "Forbindelse afbrudt" efter ~60 tokens (det gamle runs
  // hale). Vent til status forlader 'working' (gammelt run unregistreres
  // synkront i sit finally) — så tager guarden "clear & proceed fresh"-stien.
  useEffect(() => {
    if (!stream.autoContinue || !ready || stream.status === 'working') return
    const msg = stream.consumeAutoContinue()
    if (!msg) return
    const prefs = readModelPrefs()
    const sendModel = isOwner ? prefs.model : (prefs.model === 'pro' ? 'pro' : 'standard')
    const sendProvider = isOwner ? prefs.providerChoice : ''
    void doSend(msg, {
      planMode: false,
      permission,
      attachments: [],
      model: sendModel,
      providerChoice: sendProvider,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stream.autoContinue, ready, stream.status])

  // Gensend en tidligere bruger-besked (sparer copy-paste). Rolle-bevidst model
  // som auto-continue: owner bruger egne prefs, member tvinges til standard/pro.
  const resend = (text: string) => {
    const prefs = readModelPrefs()
    const sendModel = isOwner ? prefs.model : (prefs.model === 'pro' ? 'pro' : 'standard')
    const sendProvider = isOwner ? prefs.providerChoice : ''
    void doSend(text, {
      planMode: false, permission, attachments: [],
      model: sendModel, providerChoice: sendProvider,
    })
  }

  const trustBanner = trusted === false ? (
    <div className="trust-banner">
      <Lock size={14} />
      <span><strong>{effRoot}</strong> er ikke betroet — J.A.R.V.I.S. kan læse, men ikke skrive eller køre kommandoer her.</span>
      <button type="button" className="trust-btn" onClick={trustFolder}>
        <ShieldCheck size={13} /> Stol på mappen
      </button>
    </div>
  ) : null

  const workspaceSelector = (
    <div className="codeview-empty-ws">
      <div className="codeview-kind">
        <button type="button" className={kind === 'container' ? 'active' : ''} onClick={() => setKind('container')}>{serverLabel}</button>
        <button type="button" className={kind === 'workstation' ? 'active' : ''} onClick={() => setKind('workstation')}>Min computer</button>
      </div>
      {kind === 'container' ? (
        serverRoots.length > 1 ? (
          <select value={root} onChange={(e) => setRoot(e.target.value)}>
            {serverRoots.map((r) => <option key={r} value={r}>{ROOT_LABELS[r] ?? r}</option>)}
          </select>
        ) : (
          <span className="codeview-toolbar-label">{ROOT_LABELS[serverRoots[0]] ?? serverRoots[0]}</span>
        )
      ) : (
        <button type="button" className="codeview-pick" onClick={choosePath} title={wsPath || 'Vælg mappe'}>
          <FolderOpen size={13} />
          <span className="path">{wsPath || 'Vælg mappe…'}</span>
        </button>
      )}
    </div>
  )

  const composer = (
    <Composer
      streaming={stream.status === 'working'}
      onSend={handleSend}
      onStop={() => void stream.abort()}
      model="deepseek-flash"
      thinking="think"
      config={config}
      getSessionId={async () => sessionId ?? (await sessions.create('Kode-session')).id}
      showPermissions={true}
      contextTokens={contextTokens}
      overheadTokens={overheadTokens}
      compactAt={compactAt}
      compacting={compacting}
      onManualCompact={() => void triggerManualCompact('')}
      isOwner={isOwner}
      onOpenPrivacy={onOpenPrivacy}
    />
  )

  const visibleMessages = sessions.messages.filter((m) => m.role === 'user' || m.role === 'assistant')

  // Autoscroll: ved nye beskeder/stream-tokens, hold bunden hvis vi er nær den.
  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
    else if (!atBottom) setUnread((u) => u + 1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visibleMessages.length, sessionId])
  useEffect(() => {
    const el = transcriptRef.current
    if (el && atBottom) el.scrollTop = el.scrollHeight
  }, [stream.blocks, atBottom])

  const isEmpty =
    !sessionId ||
    (visibleMessages.length === 0 && stream.status === 'idle' && stream.blocks.length === 0 && !bgActive)

  const headerRight = (
    <div className="chatview-head-right">
      {config && ready && <GitChip config={config} kind={kind} root={effRoot} refreshKey={gitRefresh} />}
      <SystemHealth errors={stream.canonicalErrors} />
      <CentralBadge config={config} isOwner={isOwner} />
      {config && <ConnectionPill config={config} />}
      <button
        type="button"
        className={`panel-toggle ${envOpen ? 'active' : ''}`}
        aria-label="Vis/skjul miljø-felt" title="Miljø"
        onClick={() => setEnvManual(!(envManual ?? envWide))}
      >
        <Gauge size={16} />
      </button>
      <button
        type="button"
        className={`panel-toggle ${filesOpen ? 'active' : ''}`}
        aria-label="Vis/skjul fil-træ" title="Filer"
        onClick={() => setFilesOpen((o) => !o)}
      >
        <FolderTree size={16} />
      </button>
      <button
        type="button"
        className={`panel-toggle ${panel.open ? 'active' : ''}`}
        aria-label="Vis/skjul preview-panel" title="Preview"
        onClick={panel.toggle}
      >
        <PanelRight size={16} />
      </button>
    </div>
  )

  // Tom/ny: simpel titel (vælgeren står stort i midten).
  const header = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={bgActive && stream.status !== 'working' ? 'working' : stream.status} />{' '}
        <span className="chat-title">Code · {ready ? effRoot : 'vælg workspace'}</span>
      </div>
      {headerRight}
    </div>
  )

  // Aktiv samtale: ALT i headeren i samme stil — workspace-vælgeren foldes ind
  // ved siden af titlen, så der ikke er en separat bar nedenunder der gentager
  // stien (Bjørn 2026-06-17).
  const headerActive = (
    <div className="chatview-head">
      <div className="chatview-head-left">
        <PresenceDot status={bgActive && stream.status !== 'working' ? 'working' : stream.status} />{' '}
        <span className="chat-title">Code ·</span>
        <div className="code-head-ws">{workspaceSelector}</div>
      </div>
      {headerRight}
    </div>
  )

  // ── Tom/ny samtale: header øverst, composer centreret midt på skærmen (som chat) ──
  if (isEmpty) {
    return (
      <div className="codeview empty">
        {header}
        {trustBanner}
        <div className="chat-empty">
          <GreetingHero
            config={config}
            userName={userName ?? 'Bruger'}
            onOpenMarketplace={() => onOpenMarketplace?.()}
            onSuggest={(text) => resend(text)}
          >
            <p className="codeview-empty-hint">Hvad skal vi kode? Vælg et workspace, så går vi i gang.</p>
            {workspaceSelector}
            {composer}
          </GreetingHero>
        </div>
      </div>
    )
  }

  // ── Aktiv samtale ──
  return (
    <div className="codeview">
      <div className="codeview-main">
        {headerActive}
        {bgActive && stream.status !== 'working' && !takeoverDismissed && (
          <div className="takeover-banner" role="status">
            <span className="takeover-text">📱→🖥 Aktiv på en anden enhed — følger med her live</span>
            <button type="button" className="takeover-dismiss" aria-label="Skjul" onClick={() => setTakeoverDismissed(true)}>×</button>
          </div>
        )}
        {config && envOpen && !filesOpen && !panel.open && (
          <div className="code-right-stack">
            <EnvironmentPanel
              config={config}
              kind={kind}
              root={effRoot}
              refreshKey={gitRefresh}
              working={stream.status === 'working' || bgWorking}
              workingStep={(bgWorking ? followState.workingStep : stream.workingStep) ?? undefined}
              totalTokens={envTotalTokens}
              totalToolCalls={envTotalToolCalls}
              tools={envTools}
              sessionId={sessionId}
              hasHistory={visibleMessages.length > 0}
              isOwner={isOwner}
              onChanged={() => setGitRefresh((n) => n + 1)}
              gitMissing={gitMissing}
              installingTool={installingTool}
              onInstallTool={onInstallTool}
            />
            {isOwner && <OperatorPanel config={config} />}
          </div>
        )}
        {trustBanner}
        <div className="transcript-wrap">
        <MessageRail
          containerRef={transcriptRef}
          anchors={visibleMessages.filter((m) => m.role === 'user').map((m) => ({ id: m.id, label: railLabel(m.content) }))}
        />
        <div className="transcript" ref={transcriptRef} onScroll={onScroll}>
          {visibleMessages.map((m) => (
            <div key={m.id} data-rail-id={m.id} className="msg-block">
            <MessageRow role={m.role === 'user' ? 'user' : 'assistant'} blocks={m.content} density="compact" streaming={false} createdAt={m.created_at} onResend={m.role === 'user' ? resend : undefined} />
            </div>
          ))}
          {stream.status === 'working' && stream.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={stream.blocks} density="compact" streaming />
          )}
          {/* Cross-device: live-stream fra et run startet på en anden enhed (mobil).
              Kun når VI ikke selv streamer, så ingen dobbelt-render. */}
          {!(stream.status === 'working' && stream.blocks.length > 0) && bgActive && followState.status === 'working' && followState.blocks.length > 0 && (
            <MessageRow role="assistant" blocks={followState.blocks} density="compact" streaming />
          )}
        </div>
        </div>
        <div className="composer-area">
          {/* Liveness PERSISTENT lige over composeren (som Claude Code) — står
              altid, viser "klar" i hvile og lyser op ved et run (lokalt ELLER
              cross-device fra mobil). */}
          <LivenessIndicator
            status={bgActive && stream.status !== 'working' ? 'working' : stream.status}
            elapsedMs={bgActive && stream.status !== 'working' ? bgElapsedMs : stream.elapsedMs}
            density="compact"
            workingStep={bgActive && stream.status !== 'working' ? (followState.workingStep ?? 'vågner') : stream.workingStep}
            tokens={bgActive && stream.status !== 'working' ? followState.usage.output : stream.usage.output}
          />
          <div className="composer-notices">
            {stream.pendingApproval && (
              <ApprovalCard
                approvalId={stream.pendingApproval.approvalId}
                tool={stream.pendingApproval.tool}
                action={stream.pendingApproval.action}
                risk="medium"
                canApprove={isOwner}
                onApprove={(id) => stream.approve(id)}
                onDeny={(id) => stream.deny(id)}
              />
            )}
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
          {composer}
        </div>
      </div>
      {config && filesOpen && ready && (
        <>
          <div
            role="separator"
            aria-orientation="vertical"
            className={`codeview-panel-handle ${codePanelW.dragging ? 'dragging' : ''}`}
            onMouseDown={codePanelW.startDrag}
          />
          <div className="codeview-panel" ref={codePanelW.ref} style={{ width: codePanelW.width }}>
            <CodePanel config={config} kind={kind} root={effRoot} highlightPath={highlightPath || undefined} />
          </div>
        </>
      )}
    </div>
  )
}
