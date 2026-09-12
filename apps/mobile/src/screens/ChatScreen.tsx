import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, Animated, AppState, Linking, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import notifee, { EventType } from '@notifee/react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import { laesPins, skiftPin } from '../lib/pinnedMessages'
import { byggeKontekster, type KontekstSlags } from '../lib/recentContexts'
import { deling } from '../lib/shareModule'
import { tolkDeling, kanModtage, type DeltIntent } from '../lib/shareIntake'
import { getDeviceLocation, loadPrecision, precisionLabel, type LocationPrecision } from '../lib/location'
import { gemSomHukommelse } from '../lib/memoryApi'
import * as Clipboard from 'expo-clipboard'
import { getOrCreateDeviceIdentity } from '../lib/deviceIdentity'
import { haptik } from '../lib/haptics'
import { laesIndstillinger, gemIndstillinger, tilStreamFelter, STANDARD, type ChatIndstillinger } from '../lib/chatSettings'
import { ChatSearchBar } from '../components/ChatSearchBar'
import { ChatSettingsSheet } from '../components/ChatSettingsSheet'
import { useKeyboardHeight } from '../lib/useKeyboardHeight'
import { useConnectivity } from '../lib/useConnectivity'
import { ApprovalCard } from '../components/ApprovalCard'
import { Composer } from '../components/Composer'
import { DiffBadge } from '../components/DiffBadge'
import { ResearchStatus } from '../components/ResearchStatus'
import { useVoiceConversation } from '../lib/useVoiceConversation'
import { useComposerDictation } from '../lib/useComposerDictation'
import { VoiceOverlay } from '../components/VoiceOverlay'
import type { ContentBlock } from '../lib/sseProtocol'
import { ErrorBanner } from '../components/ErrorBanner'
import { ErrorCard } from '../components/ErrorCard'
import { GreetingHero } from '../components/GreetingHero'
import { MessageList, type MessageListHandle } from '../components/MessageList'
import { ScrollToBottom } from '../components/ScrollToBottom'
import { ModelPicker, type ModelChoice } from '../components/ModelPicker'
import { PermissionPicker, type ApprovalMode } from '../components/PermissionPicker'
import { SidePanel } from '../components/SidePanel'
import { SettingsScreen } from './SettingsScreen'
import { CameraCapture, type CapturedPhoto } from './CameraCapture'
import { AttachMenu } from '../components/AttachMenu'
import { pickDocuments, pickImagesFromGallery } from '../lib/imagePicker'
import { describeUploadError } from '../lib/uploadError'
import { cardSpacerStyle } from '../lib/floatingClearance'
import { fetchPresence, type Presence } from '../lib/companionClient'
import { livesInHousehold } from '../lib/household'
import { SensesScreen } from './SensesScreen'
import { ArtifactsScreen } from './ArtifactsScreen'
import { BillederScreen } from './BillederScreen'
import { ActivityCenterScreen } from './ActivityCenterScreen'
import {
  cancelActiveRun,
  cancelRunById,
  compactNow,
  deleteSession,
  denyTool,
  getActiveRunSnapshot,
  getContextUsage,
  getGitStatus,
  getActiveRuns,
  getModelOptions,
  renameSession,
  setSessionFlags,
  uploadAttachment,
  whoami,
  type ContextUsage,
  type GitStatus,
} from '../lib/apiClient'
import { computeUnread } from '../lib/sessionStatus'
import { loadLastSeen, markSeen } from '../lib/lastSeen'
import { loadLastSession, saveLastSession } from '../lib/sessionStore'
import { bubble } from '../lib/bubbleModule'
import {
  clearRunInProgressNotification,
  handleNotificationAction,
  showRunInProgressNotification,
  submitNotificationReply
} from '../lib/push'
import { computeRuntimePolicy } from '../lib/mobileRuntimePolicy'
import { loadBatterySaver } from '../lib/batteryPrefs'
import { enqueueOutboxItem, loadOutbox, removeOutboxItem, markOutboxFailed } from '../lib/offlineOutbox'
import { intentFromPushData, intentFromUrl, type MobileIntent } from '../lib/deepLink'
import { useAuth } from '../state/AuthContext'
import { useSessions } from '../state/SessionContext'
import { useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'
import { useStyles, useTheme, type Theme } from '../theme/ThemeContext'

// Rolle-bevidst model-valg (spejler desktop-composeren):
// member er LÅST til Standard/Pro (= ollama deepseek flash/pro, mappes
// server-side); owner får hele paletten fra /chat/visible-providers.
const MEMBER_CHOICES: ModelChoice[] = [
  { model: 'standard', providerChoice: '', label: 'Standard' },
  { model: 'pro', providerChoice: '', label: 'Pro' }
]
const OWNER_DEFAULT: ModelChoice = { model: '', providerChoice: 'deepseek', label: 'Deepseek' }

interface ChatScreenProps {
  /** Stiger når TopBars menu-knap trykkes — åbner sidepanelet. */
  openPanelSignal?: number
  /** Stiger når sync-knappen trykkes. */
  syncSignal?: number
  /** Kaldes når opdateringen er FÆRDIG — så knappen kan holde op med at snurre. */
  onSyncDone?: () => void
  /** Melder kontekst-fyldet op til headerens ring. Null = intet at vise. */
  onKontekst?: (brug: ContextUsage | null) => void
  /** Stiger når «Komprimér kontekst» vælges i tre-prik menuen. */
  compactSignal?: number
  /** Står vi i code-fladen? Panelet bruger det til at vende sit felt. */
  kodeTilstand?: boolean
  onSkiftFlade?: (tilKode: boolean) => void
  /** Titel og git-tilstand OP til code-headeren. Null = intet at vise. */
  onKodeKontekst?: (v: { titel: string; git: GitStatus | null }) => void
}

export function ChatScreen({
  openPanelSignal = 0, syncSignal = 0, onSyncDone, onKontekst, compactSignal = 0,
  kodeTilstand = false, onSkiftFlade, onKodeKontekst,
}: ChatScreenProps) {
  const tokens = useTheme()
  const styles = useStyles(makestyles)
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()
  const [panelOpen, setPanelOpen] = useState(false)

  // Fladens art ÉT sted. Fire kaldesteder henter sessioner, og de skal alle
  // fire spoerge om det samme - ellers ville en omdoebning i code-fladen
  // hente chat-listen tilbage og se ud som om samtalen forsvandt.
  const art: 'chat' | 'code' = kodeTilstand ? 'code' : 'chat'


  // TopBar ejer toppen (ChatGPT-paritet): ChatScreens egen header er fjernet.
  // Den bar LivenessRing + ConnectionPill, men ventetegnet står nu INLINE i
  // tråden som ChatGPT gør det — derfor er ringen ikke længere nødvendig, og
  // to bjælker om samme areal var det der gav «hoppen» ved tilstandsskift.
  useEffect(() => {
    if (openPanelSignal > 0) setPanelOpen(true)
  }, [openPanelSignal])

  // Sync-knappen skal GØRE noget i begge rum. I Snak henter den sessionerne
  // igen; spinneren stopper først når hentningen er færdig, så knappen aldrig
  // lyver om at være i gang.
  useEffect(() => {
    if (syncSignal <= 0 || !config) return
    let alive = true
    void sessions
      .refresh(config)
      .catch(() => {})
      .finally(() => {
        if (alive) onSyncDone?.()
      })
    return () => {
      alive = false
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [syncSignal])
  // Git-tilstanden bag code-headerens kontekstlinje OG diff-badgen over
  // komponisten. Kun i code-fladen: i chat er den hverken relevant eller
  // gratis - det er et subprocess-kald pr. opslag.
  //
  // 20 sekunder. Arbejdstraeet aendrer sig i ryk naar et vaerktoej skriver,
  // ikke jaevnt; en hurtigere puls ville koste kald uden at vise andet.
  const [git, setGit] = useState<GitStatus | null>(null)
  useEffect(() => {
    if (!config || !kodeTilstand) { setGit(null); return }
    let stoppet = false
    const hent = () => {
      getGitStatus(config)
        .then((g) => { if (!stoppet) setGit(g) })
        // Tavs, og NULSTIL. Et frossent difftal er vaerre end intet: man ville
        // tro der laa uafsluttet arbejde som for laengst er committet.
        .catch(() => { if (!stoppet) setGit(null) })
    }
    hent()
    const t = setInterval(hent, 20_000)
    return () => { stoppet = true; clearInterval(t) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, kodeTilstand])

  const aktivTitel = (sessions.sessions ?? []).find((x) => x.id === sessions.activeId)?.title || ''
  useEffect(() => {
    onKodeKontekst?.({ titel: aktivTitel, git })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [aktivTitel, git])

  // Kontekst-ringen i headeren. Tallet er BACKEND-autoritativt: desk prøvede
  // først at regne det ud af `stream.usage.input + cacheHit` og fik en ring
  // der aldrig faldt, fordi det tal indeholder systemprompten. Her spørges
  // serveren om transcript-fyldet siden sidste komprimering — dét tal falder.
  //
  // Hvert 12. sekund, ikke hvert 2,5. Ringen skal vise hvor man er, ikke
  // tælle tokens; en hurtigere puls ville koste et kald pr. bruger uden at
  // ændre et eneste ciffer man kan nå at se.
  useEffect(() => {
    const sid = sessions.activeId
    if (!config || !sid) { onKontekst?.(null); return }
    let stoppet = false
    const hent = () => {
      getContextUsage(config, sid)
        .then((brug) => { if (!stoppet) onKontekst?.(brug) })
        // Tavs: en ring der ikke kan hentes skal FORSVINDE, ikke fryse paa
        // et gammelt tal. Et frossent tal er vaerre end intet tal.
        .catch(() => { if (!stoppet) onKontekst?.(null) })
    }
    hent()
    const t = setInterval(hent, 12_000)
    return () => { stoppet = true; clearInterval(t) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [config, sessions.activeId])

  useEffect(() => {
    if (compactSignal <= 0 || !config || !sessions.activeId) return
    void compactNow(config, sessions.activeId).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [compactSignal])

  // Session-panel live-status: arbejder-prik (active-runs mens panel åbent) + ulæst.
  const [activeRunIds, setActiveRunIds] = useState<string[]>([])
  const [lastSeen, setLastSeen] = useState<Record<string, number>>({})
  useEffect(() => { void loadLastSeen().then(setLastSeen) }, [])
  useEffect(() => {
    if (!panelOpen || !config) return
    let cancelled = false
    const tick = () => { void getActiveRuns(config).then((ids) => { if (!cancelled) setActiveRunIds(ids) }).catch(() => undefined) }
    tick()
    const id = setInterval(tick, 2500)
    return () => { cancelled = true; clearInterval(id) }
  }, [panelOpen, config])
  const unreadIds = computeUnread(sessions.sessions ?? [], lastSeen, sessions.activeId)
  const listRef = useRef<MessageListHandle>(null)
  // Rul-til-bunden: vises naar man har rullet OP i traaden. Listen er inverteret,
  // saa offset 0 = nederst ved det nyeste. Taerskel paa en halv skaerm — under det
  // er man reelt stadig i bunden, og en knap ville bare staa og blinke.
  const [scrolledUp, setScrolledUp] = useState(false)
  // Chatboble: kun vis "flyt til boble"-knap hvis enheden understøtter Bubbles API.
  const [bubbleSupported, setBubbleSupported] = useState(false)
  useEffect(() => { void bubble.isSupported().then(setBubbleSupported) }, [])
  const onScrollOffset = (fromBottom: number) => {
    const up = fromBottom > 260
    setScrolledUp((prev) => (prev === up ? prev : up))
  }
  // Rul-til-bunden har to pladser: SVÆVENDE over komponisten når den hviler,
  // og INDE I komponistens knapperække mens man skriver. Ellers ville den
  // flydende knap lægge sig oven på den tekst man er i gang med.
  const [composerFocused, setComposerFocused] = useState(false)
  const jumpToBottom = useCallback(() => {
    listRef.current?.jumpBottom()
    setScrolledUp(false)
  }, [])
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [isOwner, setIsOwner] = useState(false)
  const [inHousehold, setInHousehold] = useState(false)
  const [sensesOpen, setSensesOpen] = useState(false)
  const [artifactsOpen, setArtifactsOpen] = useState(false)
  const [billederOpen, setBillederOpen] = useState(false)
  const [activityOpen, setActivityOpen] = useState(false)
  const [activityRuns, setActivityRuns] = useState<import('../lib/apiClient').ActiveRunSnapshot[]>([])
  const [outboxCount, setOutboxCount] = useState(0)
  // Livstegn. Hentes ved opstart og hvert minut — hjerteslaget slår ~hvert
  // 15. minut, så tættere polling ville kun koste strøm uden at vise mere.
  const [presence, setPresence] = useState<Presence>({ state: 'unknown' })
  useEffect(() => {
    if (!config) return
    let cancelled = false
    const tick = () => {
      void fetchPresence(config).then((p) => { if (!cancelled) setPresence(p) })
    }
    tick()
    const id = setInterval(tick, 60_000)
    return () => { cancelled = true; clearInterval(id) }
  }, [config])

  const routeIntent = useCallback((intent: MobileIntent | null) => {
    if (!intent || !config) return
    if ('sessionId' in intent && intent.sessionId) {
      sessions.select(config, intent.sessionId).catch(() => undefined)
    }
    if (intent.kind === 'run' || intent.kind === 'approval') {
      setActivityOpen(true)
    } else if (intent.kind === 'artifact') {
      setArtifactsOpen(true)
    } else if (intent.kind === 'memory') {
      setSettingsOpen(true)
    } else if (intent.kind === 'settings') {
      setSettingsOpen(true)
    }
  }, [config, sessions])

  useEffect(() => {
    const openUrl = ({ url }: { url: string }) => routeIntent(intentFromUrl(url))
    const sub = Linking.addEventListener('url', openUrl)
    void Linking.getInitialURL().then((url) => { if (url) routeIntent(intentFromUrl(url)) }).catch(() => undefined)
    return () => sub.remove()
  }, [routeIntent])
  const [cameraOpen, setCameraOpen] = useState(false)
  const [attachMenuOpen, setAttachMenuOpen] = useState(false)
  // FEATURE2/BUG3: valgt/taget billede lægger sig som ventende vedhæftning i
  // composeren (auto-sendes IKKE) så man kan skrive en besked til.
  // FLERE vedhæftninger pr. besked. Med kun én kunne man ikke sende to
  // skærmbilleder sammen — man skulle sende to beskeder, og så mistede Jarvis
  // sammenhængen mellem dem.
  const [pendingAttachments, setPendingAttachments] = useState<
    { id: string; uploadId?: string; uri: string; name: string; mime: string; status?: 'uploading' | 'ready' | 'error'; progress?: number }[]
  >([])
  const [displayName, setDisplayName] = useState('Jarvis')
  const [modelChoices, setModelChoices] = useState<ModelChoice[]>([])
  const [modelPickerOpen, setModelPickerOpen] = useState(false)
  const [permissionPickerOpen, setPermissionPickerOpen] = useState(false)
  // Indstillinger PR. SAMTALE. Én samtale kan handle om kode og en anden om
  // aftaler; de har ikke brug for samme model eller samme værktøjs-omfang.
  const [chatCfg, setChatCfg] = useState<ChatIndstillinger>(STANDARD)
  const [chatCfgOpen, setChatCfgOpen] = useState(false)
  const [soegAaben, setSoegAaben] = useState(false)
  const insets = useSafeAreaInsets()
  const [pins, setPins] = useState<string[]>([])
  // Kontekst-striben i vedhæft-fladen. Tilstanden hentes når fladen ÅBNES —
  // ikke løbende: en tilladelse man lige har ændret skal være med, men en
  // baggrunds-poll af udklipsholderen ville være at lytte uopfordret.
  const [ctxPraecision, setCtxPraecision] = useState<LocationPrecision>('off')
  const [ctxUdklip, setCtxUdklip] = useState(false)
  const [indsaet, setIndsaet] = useState<{ tekst: string; n: number }>({ tekst: '', n: 0 })
  const [enhedsNavn, setEnhedsNavn] = useState('')
  const connectivity = useConnectivity(config ?? null)
  // Server-side run-status for den aktive session (delt sandhed via /chat/active-
  // runs). Forhindrer at man sender ind i et kørende svar (= nudge-swallow,
  // "han reagerer ikke"), og henter svaret når runnet er færdigt. Matcher
  // Claude/ChatGPT: composeren viser "stop" mens serveren arbejder.
  const [serverBusy, setServerBusy] = useState(false)
  const [activeRunId, setActiveRunId] = useState('')
  const [appState, setAppState] = useState(AppState.currentState)
  const [batterySaver, setBatterySaver] = useState(false)
  const serverBusyRef = useRef(false)
  const keyboardHeight = useKeyboardHeight()
  // Løft composeren op over tastaturet med fuld tastaturhøjde. (Tidligere
  // trak vi insets.bottom fra, men keyboardHeight inkluderer allerede
  // navigationslinjen i edge-to-edge → det dobbelt-fratrak og lod composeren
  // ligge lidt skjult. Fuld højde sikrer den altid er fri af tastaturet.)
  const liftPadding = keyboardHeight
  // Komponisten SVÆVER over indholdet. Godkendelses- og fejlkort ligger i den
  // almindelige kolonne og endte derfor UNDER den — Bjørn kunne se kortet, men
  // ikke nå knapperne (3. sept.). Vi måler komponistens faktiske højde frem for
  // at gætte en konstant: den skifter mellem hvileform, arbejdsform og
  // vedhæftnings-chips, og et fast tal ville være forkert i mindst én af dem.
  const [composerHeight, setComposerHeight] = useState(96)

  const didRestore = useRef(false)
  const policy = computeRuntimePolicy({
    appState,
    connectivity,
    activeRun: stream.state.status === 'working' || serverBusy,
    userViewingActiveSession: true,
    batterySaver
  })

  useEffect(() => {
    void loadBatterySaver().then(setBatterySaver)
  }, [])

  // Blød session-overgang (§3.6): fade besked-fladen ind ved samtale-skift.
  const sessionFade = useRef(new Animated.Value(1)).current
  useEffect(() => {
    sessionFade.setValue(0)
    Animated.timing(sessionFade, { toValue: 1, duration: tokens.motion.durBase, useNativeDriver: true }).start()
  }, [sessions.activeId, sessionFade])

  // Notifikations-tap → åbn den relevante samtale (dyb-link). Dækker både tap
  // mens appen er åben (onForegroundEvent) og koldstart fra en notifikation
  // (getInitialNotification). session_id kommer fra den data-only FCM-besked.
  useEffect(() => {
    if (!config) return
    let cancelled = false
    const open = (sid: unknown) => {
      const id = typeof sid === 'string' ? sid : ''
      if (id) sessions.select(config, id).catch(() => undefined)
    }
    const unsub = notifee.onForegroundEvent(({ type, detail }) => {
      if (type === EventType.PRESS) {
        routeIntent(intentFromPushData(detail.notification?.data as Record<string, unknown> | undefined))
        open(detail.notification?.data?.session_id)
      }
      // Direct Reply mens appen er i forgrunden (bruger trækker shade ned).
      if (type === EventType.ACTION_PRESS && config) {
        void handleNotificationAction(config, detail).then((result) => {
          if (result === 'open') routeIntent(intentFromPushData(detail.notification?.data as Record<string, unknown> | undefined))
        })
      }
    })
    void notifee.getInitialNotification().then((n) => {
      if (!cancelled) {
        routeIntent(intentFromPushData(n?.notification?.data as Record<string, unknown> | undefined))
        open(n?.notification?.data?.session_id)
      }
    })
    return () => {
      cancelled = true
      unsub()
    }
  }, [config, routeIntent])

  useEffect(() => {
    let cancelled = false
    const refresh = () => { void loadOutbox().then((items) => { if (!cancelled) setOutboxCount(items.length) }) }
    refresh()
    const id = setInterval(refresh, 5000)
    return () => { cancelled = true; clearInterval(id) }
  }, [])

  useEffect(() => {
    if (!config || connectivity !== 'connected') return
    let cancelled = false
    const flush = async () => {
      const items = await loadOutbox()
      for (const item of items) {
        if (cancelled) return
        try {
          if (item.kind === 'chat_message') {
            stream.send(config, item.sessionId, item.text, {
              ...item.controls,
              attachmentIds: item.attachmentIds,
            })
          } else if (item.kind === 'approval_action') {
            if (item.action === 'approve') {
              // Approval-id'er deles mellem chat/work; endpointet er serverens sandhed.
              const { approveTool } = await import('../lib/apiClient')
              await approveTool(config, item.approvalId)
            } else {
              await denyTool(config, item.approvalId)
            }
          } else if (item.kind === 'run_action' && item.action === 'stop') {
            await cancelRunById(config, item.runId)
          }
          await removeOutboxItem(item.id)
        } catch (e) {
          await markOutboxFailed(item.id, e instanceof Error ? e.message : 'Kunne ikke sende')
        }
      }
      setOutboxCount((await loadOutbox()).length)
    }
    void flush()
    return () => { cancelled = true }
  }, [config, connectivity])

  useEffect(() => {
    if (!config) return
    sessions.refresh(config, art).catch(() => undefined)
    whoami(config)
      .then((me) => {
        setDisplayName(me.display_name || 'Jarvis')
        setIsOwner(me.role === 'owner')
        // Arkiv-indgangen følger HUSSTANDEN, ikke owner-rollen: Michelle bor
        // her og deler det rum Jarvis sanser. Serveren er stadig den ægte
        // grænse — dette skjuler bare en indgang der allerede er lukket.
        setInHousehold(livesInHousehold(me))
        if (me.role === 'owner') {
          // Owner: hele paletten (deepseek-default forrest).
          getModelOptions(config)
            .then((opts) => {
              const choices = [OWNER_DEFAULT, ...opts.map((o) => ({ model: o.model, providerChoice: o.provider, label: o.label }))]
              setModelChoices(choices)
            })
            .catch(() => {
              setModelChoices([OWNER_DEFAULT])
            })
        } else {
          // Member/guest: låst til Standard/Pro.
          setModelChoices(MEMBER_CHOICES)
        }
      })
      .catch(() => undefined)
    // Gendan den session brugeren sidst var i — OG den flade den hørte til.
    //
    // Fladen gendannes FØRST. Bjørn 12/9-2026: «appen glemmer code mode så
    // starter den stadig op i chat mode med en code session loaded». Sætter
    // man sessionen først, står man et øjeblik i chat-fladen med en
    // code-samtale og en chat-liste — præcis den modstrid han beskrev.
    if (!didRestore.current) {
      didRestore.current = true
      loadLastSession().then((plads) => {
        if (!plads) return
        if (plads.kode !== kodeTilstand) onSkiftFlade?.(plads.kode)
        sessions.select(config, plads.id)
          .then((s) => {
            // SESSIONEN HAR DET SIDSTE ORD. Den gemte flade er et minde;
            // samtalens `kind` er et faktum. De to kan kun være uenige i ét
            // tilfælde — nøglen fra før fladen blev husket indeholdt kun et
            // id — og netop dér ville man lande i chat-fladen med en
            // code-samtale, som er præcis det Bjørn beskrev.
            const kode = s.kind === 'code'
            if (kode !== plads.kode) onSkiftFlade?.(kode)
          })
          .catch(() => undefined)
      })
    }
  }, [config])

  // Skift af flade henter listen om. EGEN effekt frem for at haenge `art` paa
  // [config]: den ovenfor kalder ogsaa whoami og gendanner sidste session, og
  // begge dele ville koere igen hver gang man trykkede Code.
  //
  // Foerste gang springes over - effekten ovenfor har lige hentet.
  const forrigeArt = useRef(art)
  useEffect(() => {
    if (forrigeArt.current === art) return
    forrigeArt.current = art
    if (config) sessions.refresh(config, art).catch(() => undefined)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [art, config])

  // Husk aktiv session OG flade på tværs af app-luk. Begge, altid, i samme
  // skrivning — to nøgler kan blive uenige, én kan ikke. `kodeTilstand` står
  // derfor også i afhængighederne: skifter man flade uden at skifte samtale,
  // skal det også huskes.
  useEffect(() => {
    if (sessions.activeId) void saveLastSession(sessions.activeId, kodeTilstand)
  }, [sessions.activeId, kodeTilstand])

  // Stream dør når appen baggrunder (Android dræber SSE), men kørslen fortsætter
  // server-side. Når appen kommer tilbage i forgrunden, gen-synkroniserer vi den
  // aktive session så svaret der blev færdigt mens man var væk, dukker op.
  const appStateRef = useRef(AppState.currentState)
  useEffect(() => {
    const sub = AppState.addEventListener('change', (next) => {
      const prev = appStateRef.current
      appStateRef.current = next
      setAppState(next)
      if (next.match(/inactive|background/) && (stream.state.status === 'working' || serverBusy)) {
        stream.detachForBackground()
        void showRunInProgressNotification(
          sessions.activeId ?? undefined,
          stream.state.activeRunId ?? activeRunId
        )
      }
      if (prev.match(/inactive|background/) && next === 'active' && config && sessions.activeId) {
        void clearRunInProgressNotification()
        void loadBatterySaver().then(setBatterySaver)
        // KOBL PAA IGEN hvis runnet stadig kører. Det her manglede: linjen
        // nedenfor henter BESKEDER, og det dækker et run der blev færdigt mens
        // man var væk. Var det stadig i gang, var der ingen live-vej tilbage —
        // turen så død ud indtil man lukkede appen helt og startede forfra.
        stream.genoptagKoerende(config)
        // Gen-synkronisér: A3 lader runnet køre færdigt server-side mens appen er
        // i baggrunden → ved retur henter vi sessionen så det færdige svar vises.
        // Begge dele: den ene dækker "blev færdig", den anden "kører endnu".
        sessions.select(config, sessions.activeId).catch(() => undefined)
      }
    })
    return () => sub.remove()
  }, [config, sessions.activeId, stream, serverBusy, activeRunId])

  // Poll server-side run-status for den aktive session (delt sandhed). Mens et
  // run kører: vis "arbejder" (composeren blokerer send → ingen nudge-swallow).
  // Når det skifter fra kørende→færdig: hent sessionen så svaret dukker op (også
  // svar startet på en anden enhed / efter baggrund). Rører ALDRIG send-streamens
  // state (modsat den fjernede follow-subscription).
  useEffect(() => {
    if (!config || !sessions.activeId) {
      setServerBusy(false)
      serverBusyRef.current = false
      return
    }
    const sid = sessions.activeId
    let cancelled = false
    const tick = async () => {
      try {
        const runs = await getActiveRunSnapshot(config)
        if (cancelled) return
        const match = runs.find((r) => r.sessionId === sid)
        const busy = Boolean(match)
        const was = serverBusyRef.current
        serverBusyRef.current = busy
        setServerBusy(busy)
        setActiveRunId(match?.runId ?? '')
        // idle → kørende: et run startede i sessionen. Live-attach (delt-session
        // sync) — stream.follow rører IKKE noget hvis vi selv sender (guard'en
        // tjekker control.current). Så ser vi en anden enheds/Jarvis' run live.
        if (!was && busy) stream.follow(config, sid)
        // kørende → færdig: svaret er nu persisteret → hent det ind (+ stop attach).
        if (was && !busy) {
          stream.stopFollow()
          sessions.select(config, sid).catch(() => undefined)
        }
      } catch {
        /* behold sidste — ingen flicker ved netværks-blip */
      }
    }
    void tick()
    const id = policy.activeRunPollMs > 0 ? setInterval(() => void tick(), policy.activeRunPollMs) : null
    return () => {
      cancelled = true
      if (id) clearInterval(id)
    }
  }, [config, sessions.activeId, policy.activeRunPollMs])

  // Greeting vises når chatten er tom (opstart / ny samtale) — som på desktop.
  const showGreeting = sessions.messages.length === 0 && !sessions.loading

  useEffect(() => {
    let levende = true
    const sid = sessions.activeId
    if (!sid) { setChatCfg(STANDARD); return }
    laesIndstillinger(sid)
      .then((c) => { if (levende) setChatCfg(c) })
      .catch(() => { if (levende) setChatCfg(STANDARD) })
    return () => { levende = false }
  }, [sessions.activeId])

  const ensureSessionAndSend = async (text: string) => {
    if (!config) return
    if (pendingAttachments.some((a) => a.status === 'uploading')) return
    if (connectivity === 'offline') {
      if (!sessions.activeId) {
        Alert.alert('Offline', 'Åbn en eksisterende samtale før du køer en besked offline.')
        return
      }
      await enqueueOutboxItem({
        kind: 'chat_message',
        sessionId: sessions.activeId,
        text,
        attachmentIds: pendingAttachments.filter((a) => a.status !== 'error' && a.status !== 'uploading').map((a) => a.uploadId ?? a.id),
        controls: tilStreamFelter(chatCfg),
      })
      setOutboxCount((await loadOutbox()).length)
      setPendingAttachments([])
      return
    }
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    if (!sessions.activeId) void gemIndstillinger(sessionId, chatCfg)
    const readyAttachments = pendingAttachments.filter((a) => a.status !== 'error' && a.status !== 'uploading')
    const attachmentIds = readyAttachments.length
      ? readyAttachments.map((a) => a.uploadId ?? a.id)
      : undefined
    const cfg = tilStreamFelter(chatCfg)
    stream.send(config, sessionId, text, {
      ...cfg,
      attachmentIds,
    })
    setPendingAttachments([])
  }

  // Samtale-mode (Trin 3): voice-hook. sendMessage=ensureSessionAndSend, text fra text-blocks.
  const _voiceExtract = (blocks: ContentBlock[]) =>
    (blocks || []).filter((b) => (b as { type?: string }).type === 'text')
      .map((b) => String((b as { text?: string }).text || '')).join(' ').trim()
  const voice = useVoiceConversation(config, {
    status: stream.state.status,
    blocks: stream.state.blocks,
    sendMessage: (t: string) => { void ensureSessionAndSend(t) },
    extractText: _voiceExtract,
    readAllResponses: chatCfg.stemme,
  })
  const dictation = useComposerDictation(config)
  const dictationSequence = useRef(0)
  const dictationCancelRef = useRef(dictation.cancel)
  const dictationSessionRef = useRef(sessions.activeId)
  useEffect(() => { dictationCancelRef.current = dictation.cancel }, [dictation.cancel])

  useEffect(() => {
    if (!dictation.text) return
    dictationSequence.current += 1
    setIndsaet({ tekst: dictation.text, n: dictationSequence.current })
    dictation.clearResult()
  }, [dictation.text, dictation.clearResult])

  useEffect(() => {
    if (String(appState).match(/inactive|background/)) void dictationCancelRef.current()
  }, [appState])

  useEffect(() => {
    if (dictationSessionRef.current !== sessions.activeId) {
      dictationSessionRef.current = sessions.activeId
      void dictationCancelRef.current()
    }
  }, [sessions.activeId])

  // Upload billede (kamera/galleri) → stage som ventende vedhæftning i composeren
  // (BUG3: ikke auto-send). Sendes når brugeren trykker send, med valgfri besked.
  const stageAttachment = async (photo: CapturedPhoto) => {
    await stageAttachments([photo])
  }

  /**
   * Upload flere filer og læg dem i komponisten som ventende vedhæftninger.
   *
   * Hver fil uploades for sig, og en enkelt der fejler stopper ikke resten —
   * serveren kan afvise ÉN fil (malware, et arkiv der ikke kunne pakkes
   * sikkert ud) uden at de andre er noget i vejen med. Brugeren får at vide
   * hvilke der ikke kom med, i stedet for en samlet «det gik galt».
   */
  const stageAttachments = async (files: CapturedPhoto[]) => {
    if (!config || !files.length) return
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    const failed: string[] = []
    for (const f of files) {
      const localId = `local-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`
      setPendingAttachments((prev) => [
        ...prev,
        { id: localId, uri: f.uri, name: f.name, mime: f.mime, status: 'uploading', progress: 1 }
      ])
      try {
        const up = await uploadAttachment(config, sessionId, f, (progress) => {
          setPendingAttachments((prev) => prev.map((item) => (
            item.id === localId ? { ...item, progress, status: 'uploading' } : item
          )))
        })
        setPendingAttachments((prev) => prev.map((item) => (
          item.id === localId ? { ...item, uploadId: up.id, status: 'ready', progress: 100 } : item
        )))
      } catch (e) {
        setPendingAttachments((prev) => prev.map((item) => (
          item.id === localId ? { ...item, status: 'error', progress: 0 } : item
        )))
        failed.push(`${f.name}${describeUploadError(e)}`)
      }
    }
    if (failed.length) {
      Alert.alert(
        failed.length === 1 ? 'Filen kom ikke med' : 'Nogle filer kom ikke med',
        failed.join('\n')
      )
    }
  }

  const handleCapture = async (photo: CapturedPhoto) => {
    setCameraOpen(false)
    await stageAttachment(photo)
  }

  const handlePickGallery = async () => {
    setAttachMenuOpen(false)
    await stageAttachments(await pickImagesFromGallery())
  }

  const handlePickDocuments = async () => {
    setAttachMenuOpen(false)
    await stageAttachments(await pickDocuments())
  }

  useEffect(() => {
    const id = sessions.activeId
    if (!id) { setPins([]); return }
    let levende = true
    laesPins(id).then((p) => { if (levende) setPins(p) }).catch(() => undefined)
    return () => { levende = false }
  }, [sessions.activeId])

  const handleTogglePin = (messageId: string) => {
    const id = sessions.activeId
    if (!id) return
    void haptik('markér')
    skiftPin(id, messageId).then(setPins).catch(() => undefined)
  }

  const handleSaveMemory = (message: { id?: string; content: string }) => {
    if (!config) return
    void haptik('markér')
    gemSomHukommelse(
      config, message.content, sessions.activeId ?? undefined, message.id ? String(message.id) : undefined
    ).then((r) => {
      // Kvitteringen er hele pointen: uden den ved man ikke om han fik den.
      Alert.alert(r.ok ? 'Husket' : 'Ikke gemt', r.besked)
    })
  }

  // Deling udefra: Android har haft filtrene siden 0.2.16, men INGEN har
  // læst dem — en dør uden nogen bag. Nu lander det delte i komposeren.
  // Det sendes IKKE af sig selv: man skal kunne skrive hvad der skal ske
  // med det, før han går i gang.
  useEffect(() => {
    const modtag = (intent: DeltIntent) => {
      if (!kanModtage(intent.mimeType)) {
        Alert.alert('Kan ikke tage imod', 'Jarvis kan tage imod tekst, billeder og PDF.')
        return
      }
      const h = tolkDeling(intent)
      if (h.slags === 'ingenting') return
      if (h.slags === 'filer') {
        void stageAttachments(
          h.uris.map((uri, i) => ({ uri, name: `delt-${i + 1}`, mime: intent.mimeType || 'application/octet-stream' }))
        )
      }
      if (h.udkast) setIndsaet((p) => ({ tekst: h.udkast, n: p.n + 1 }))
    }
    void deling.vedOpstart().then((i) => { if (i) modtag(i) })
    return deling.lyt(modtag)
  }, [])

  // Kaldes når vedhæft-fladen åbnes: to billige opslag, ikke en poll.
  const opdaterKontekst = () => {
    loadPrecision().then(setCtxPraecision).catch(() => undefined)
    getOrCreateDeviceIdentity().then((d) => setEnhedsNavn(d.deviceName)).catch(() => undefined)
    Clipboard.hasStringAsync().then(setCtxUdklip).catch(() => setCtxUdklip(false))
  }

  const handleKontekst = async (slags: KontekstSlags) => {
    void haptik('markér')
    if (slags === 'kamera') { setAttachMenuOpen(false); setCameraOpen(true); return }
    if (slags === 'fil') { await handlePickDocuments(); return }
    if (slags === 'udklip') {
      const t = await Clipboard.getStringAsync().catch(() => '')
      if (t.trim()) { setAttachMenuOpen(false); setIndsaet((p) => ({ tekst: t, n: p.n + 1 })) }
      return
    }
    if (slags === 'enhed') {
      setAttachMenuOpen(false)
      setIndsaet((p) => ({ tekst: `Jeg skriver fra ${enhedsNavn || 'denne enhed'}.`, n: p.n + 1 }))
      return
    }
    // Lokation: hentes FØRST når man beder om den, og med den præcision
    // Bjørn har valgt i indstillinger — ikke den bedste enheden kan give.
    const pos = await getDeviceLocation(ctxPraecision).catch(() => null)
    setAttachMenuOpen(false)
    if (!pos) { Alert.alert('Ingen lokation', `Kunne ikke hente en position (${precisionLabel(ctxPraecision)}).`); return }
    setIndsaet((p) => ({ tekst: `Jeg er her: ${pos.label}`, n: p.n + 1 }))
  }

  const handleSelectSession = (sessionId: string) => {
    setPanelOpen(false)
    const s = (sessions.sessions ?? []).find((x) => x.id === sessionId)
    const count = s?.message_count ?? 0
    setLastSeen((prev) => ({ ...prev, [sessionId]: count }))
    void markSeen(sessionId, count)
    if (config) sessions.select(config, sessionId).catch(() => undefined)
  }

  const handleNewSession = () => {
    setPanelOpen(false)
    // I code-fladen faar den desk's eget navn. Der findes INGEN markoer paa en
    // code-session - hverken kolonne eller felt; maalt 12/9-2026 er «Kode-session»
    // udelukkende den titel desk's CodeView giver ved oprettelse. Derfor kan
    // listen ikke filtreres aerligt (et omdoebt navn ville forsvinde, og en
    // chat med samme titel ville dukke op), men EN NY kan godt hedde det samme
    // paa begge enheder.
    if (config) sessions.create(config, kodeTilstand ? 'Kode-session' : 'Ny samtale', art).catch(() => undefined)
  }

  const lastUserMessage = [...sessions.messages].reverse().find((message) => message.role === 'user')
  const canRetry =
    !!lastUserMessage && (stream.state.status === 'interrupted' || stream.state.status === 'error')
  // Er der overhovedet et kort at gøre plads til? Afgør om afstandsklodsen
  // nedenfor findes — en klods uden noget at holde afstand fra er bare et hul.
  const hasCard = canRetry || Boolean(stream.approval && config)

  return (
    <View style={styles.root}>
      {connectivity !== 'connected' ? (
        <View style={[styles.connBanner, connectivity === 'offline' ? styles.connOffline : styles.connReconnect]}>
          <Text style={styles.connText}>
            {connectivity === 'offline' ? 'Offline — venter på forbindelse' : 'Genopretter forbindelse til Jarvis…'}
          </Text>
        </View>
      ) : stream.reconnecting ? (
        <View style={[styles.connBanner, styles.connReconnect]}>
          <Text style={styles.connText}>Genforbinder — Jarvis arbejder videre…</Text>
        </View>
      ) : null}

      <View style={styles.flex}>
        {/* Svæver ligesom TopBar og komponisten. Som almindeligt søskende-
            element ville feltet lande i y=0 — altså BAG den svævende
            topbjælke, hvor man hverken kan se eller ramme det.
            insets.top + 52 = under bjælken; tråden ruller videre bagved. */}
        <View style={[styles.floatSearch, { top: insets.top + 52 }]} pointerEvents="box-none">
        <ChatSearchBar
          visible={soegAaben}
          messages={sessions.messages}
          onJump={(id) => listRef.current?.jumpToMessage(id)}
          onClose={() => setSoegAaben(false)}
        />
        </View>
        <Animated.View style={{ flex: 1, opacity: sessionFade }}>
          {showGreeting ? (
            <GreetingHero userName={displayName} presence={presence} />
          ) : (
            <MessageList
              ref={listRef}
              messages={sessions.messages}
              blocks={stream.state.blocks}
              onResend={(text) => void ensureSessionAndSend(text)}
              pins={pins}
              onTogglePin={sessions.activeId ? handleTogglePin : undefined}
              onSaveMemory={config ? handleSaveMemory : undefined}
              onScrollOffset={onScrollOffset}
              thinking={stream.state.status === 'working' || serverBusy}
              bottomInset={liftPadding}
            />
          )}
        </Animated.View>
        {!showGreeting ? (
          <ScrollToBottom
            visible={scrolledUp && !composerFocused && sessions.messages.length >= 2}
            bottom={liftPadding + 84}
            onPress={jumpToBottom}
          />
        ) : null}
        {/* Kortene skal stå OVER den svævende komponist, ikke bag den.
            Men KUN når der faktisk er et kort. Første udgave gav indpakningen
            bundmargen ubetinget, og så åd en tom kasse pladsen mellem tråden og
            komponisten — og med tastaturet fremme voksede marginen med
            tastaturets højde og skubbede hele tråden ud af skærmen.
            En afstandsklods skal kun findes, når der er noget at holde afstand
            fra. */}
        <View
          style={cardSpacerStyle(hasCard, composerHeight, liftPadding)}
          pointerEvents="box-none"
        >
        {canRetry ? (
          stream.streamError && stream.streamError.kind ? (
            // Kanonisk fejl (Canonical Error System, Fase 2): rigt kort med titel,
            // hvad-systemet-gjorde og fix_hint.
            <ErrorCard
              error={stream.streamError}
              onRetry={
                stream.streamError.retryable
                  ? () => {
                      stream.clearError()
                      void ensureSessionAndSend(lastUserMessage.content)
                    }
                  : undefined
              }
              onDismiss={() => stream.clearError()}
            />
          ) : (
            <ErrorBanner
              title={
                stream.streamError
                  ? stream.streamError.message
                  : stream.state.status === 'interrupted'
                    ? 'Svar stoppet'
                    : 'Stream fejlede'
              }
              detail={
                stream.streamError?.fixHint
                  ? stream.streamError.fixHint
                  : 'Du kan prøve den seneste besked igen.'
              }
              actionLabel={!stream.streamError || stream.streamError.retryable ? 'Prøv igen' : undefined}
              onAction={
                !stream.streamError || stream.streamError.retryable
                  ? () => {
                      stream.clearError()
                      void ensureSessionAndSend(lastUserMessage.content)
                    }
                  : undefined
              }
              onDismiss={stream.streamError ? () => stream.clearError() : undefined}
            />
          )
        ) : null}
        {stream.approval && config ? (
          <ApprovalCard
            approval={stream.approval}
            onApprove={() => void stream.approve(config)}
            onDeny={() => void stream.deny(config)}
          />
        ) : null}
        </View>
        {/* Komponisten SVÆVER: tråden ruller bag den, som i ChatGPT-appen.
            Den løftes selv af tastaturet (bottom: liftPadding) frem for at
            containeren skubbes — ellers ville listen blive kortere og
            rulle-positionen hoppe hver gang tastaturet kom frem. */}
        <View
          style={[styles.floatBottom, { bottom: liftPadding }]}
          pointerEvents="box-none"
          onLayout={(e) => {
            const h = Math.round(e.nativeEvent.layout.height)
            setComposerHeight((prev) => (Math.abs(prev - h) > 1 ? h : prev))
          }}
        >
        <ResearchStatus research={stream.state.research} />
        {/* Lige OVER komponisten, som i Codex. Den tegner sig selv vaek naar
            traeet er rent - se DiffBadge for hvorfor det ikke er «0 filer». */}
        <DiffBadge git={kodeTilstand ? git : null} />
        <Composer
          indsaet={indsaet}
          disabled={!config || pendingAttachments.some((a) => a.status === 'uploading')}
          working={stream.state.status === 'working' || serverBusy}
          modelLabel={chatCfg.model?.label ?? modelChoices[0]?.label}
          onSend={ensureSessionAndSend}
          onStop={() => {
            if (!config) return
            // Streamer vi selv → stop lokalt; ellers afbryd serverens run for
            // sessionen (fx et run der fortsatte mens appen var i baggrunden).
            if (stream.state.status === 'working') {
              void stream.stop(config)
            } else if (serverBusy && sessions.activeId) {
              void cancelActiveRun(config, sessions.activeId).catch(() => undefined)
            }
          }}
          onPressModel={() => setModelPickerOpen(true)}
          onAttach={() => { opdaterKontekst(); setAttachMenuOpen(true) }}
          onDictate={() => {
            voice.exit()
            void dictation.start()
          }}
          onConversation={() => {
            void dictation.cancel()
            voice.enter()
          }}
          dictationState={dictation.state}
          dictationElapsedMs={dictation.elapsedMs}
          dictationError={dictation.error}
          dictationLevel={dictation.level}
          onStopDictation={() => { void dictation.stop() }}
          onCancelDictation={() => { void dictation.cancel() }}
          attachments={pendingAttachments}
          onRemoveAttachment={(id) =>
            setPendingAttachments((prev) => prev.filter((a) => a.id !== id))
          }
          onFocusChange={setComposerFocused}
          showJumpToBottom={scrolledUp && composerFocused}
          onJumpToBottom={jumpToBottom}
          researchMode={chatCfg.researchMode === 'on'}
          onResearchModeChange={(enabled) => {
            const next = { researchMode: enabled ? 'on' as const : 'off' as const }
            const sid = sessions.activeId
            setChatCfg((current) => ({ ...current, ...next }))
            if (sid) void gemIndstillinger(sid, next).then(setChatCfg).catch(() => undefined)
          }}
          permission={chatCfg.spoergFoerst ? 'ask' : 'trust'}
          onPressPermission={() => setPermissionPickerOpen(true)}
        />
        </View>
      </View>

      <ModelPicker
        open={modelPickerOpen}
        choices={modelChoices}
        selectedLabel={chatCfg.model?.label ?? modelChoices[0]?.label}
        thinkingMode={chatCfg.thinkingMode}
        onThinkingModeChange={(thinkingMode) => {
          const sid = sessions.activeId
          const next = { thinkingMode }
          setChatCfg((current) => ({ ...current, ...next }))
          if (sid) void gemIndstillinger(sid, next).then(setChatCfg).catch(() => undefined)
        }}
        onSelect={(m) => {
          const sid = sessions.activeId
          const model = m.model ? m : null
          setChatCfg((current) => ({ ...current, model }))
          if (sid) void gemIndstillinger(sid, { model }).then(setChatCfg).catch(() => undefined)
        }}
        onClose={() => setModelPickerOpen(false)}
      />

      <PermissionPicker
        open={permissionPickerOpen}
        selected={chatCfg.spoergFoerst ? 'ask' : 'trust'}
        onSelect={(mode: ApprovalMode) => {
          const next = { spoergFoerst: mode === 'ask' }
          const sid = sessions.activeId
          setChatCfg((current) => ({ ...current, ...next }))
          if (sid) void gemIndstillinger(sid, next).then(setChatCfg).catch(() => undefined)
        }}
        onClose={() => setPermissionPickerOpen(false)}
      />

      {config ? (
        <SidePanel
          open={panelOpen}
          onClose={() => setPanelOpen(false)}
          displayName={displayName}
          config={config}
          kodeTilstand={kodeTilstand}
          onSkiftFlade={onSkiftFlade
            ? (tilKode) => { onSkiftFlade(tilKode); setPanelOpen(false) }
            : undefined}
          sessions={sessions.sessions}
          activeId={sessions.activeId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          workingIds={activeRunIds}
          unreadIds={unreadIds}
          onSessionAction={(h) => {
            if (!config) return
            // Handlingen udfoeres OG listen hentes igen. Uden opfriskningen
            // ville en fastgjort samtale blive staaende hvor den var, og en
            // slettet blive staaende helt — serveren er den der bestemmer
            // raekkefoelgen, ikke klienten.
            const efter = () => { void sessions.refresh(config, art) }
            if (h.slags === 'rename' && h.titel) {
              void renameSession(config, h.id, h.titel).then(efter).catch(() => undefined)
            } else if (h.slags === 'delete') {
              void deleteSession(config, h.id).then(() => {
                // Slettede man den man stod i, skal skaermen ikke blive ved med
                // at vise en samtale der ikke findes.
                if (sessions.activeId === h.id) void sessions.refresh(config, art)
                efter()
              }).catch(() => undefined)
            } else if (h.slags === 'flags' && h.flags) {
              void setSessionFlags(config, h.id, h.flags).then(efter).catch(() => undefined)
            }
          }}
          isOwner={inHousehold}
          onOpenSenses={() => {
            setPanelOpen(false)
            setSensesOpen(true)
          }}
          onOpenArtifacts={() => {
            setPanelOpen(false)
            setArtifactsOpen(true)
          }}
          onOpenBilleder={() => {
            setPanelOpen(false)
            setBillederOpen(true)
          }}
          onOpenActivity={() => {
            setPanelOpen(false)
            setActivityOpen(true)
            if (config) {
              void getActiveRunSnapshot(config).then(setActivityRuns).catch(() => undefined)
              void loadOutbox().then((items) => setOutboxCount(items.length))
            }
          }}
          onOpenSettings={() => {
            setPanelOpen(false)
            setSettingsOpen(true)
          }}
          onOpenChatSettings={sessions.activeId ? () => {
            setPanelOpen(false)
            setChatCfgOpen(true)
          } : undefined}
          bubbleSupported={bubbleSupported}
          onFloatActive={() => {
            const id = sessions.activeId
            if (!id) return
            const title = (sessions.sessions ?? []).find((s) => s.id === id)?.title || 'Jarvis'
            bubble.floatCurrentChat(id, title)
          }}
        />
      ) : null}

      <ChatSettingsSheet
        visible={chatCfgOpen}
        onSearch={() => setSoegAaben(true)}
        cfg={chatCfg}
        modeller={modelChoices.filter((c) => c.model)}
        onChange={(next) => {
          const sid = sessions.activeId
          if (!sid) return
          // Optimistisk: kontakten skal føles øjeblikkelig, og et fejlet skriv
          // må ikke rulle UI'et tilbage midt under fingeren.
          setChatCfg((nu) => ({ ...nu, ...next }))
          void gemIndstillinger(sid, next).then(setChatCfg).catch(() => undefined)
        }}
        onClose={() => setChatCfgOpen(false)}
      />

      <Modal visible={settingsOpen} animationType="slide" onRequestClose={() => setSettingsOpen(false)}>
        <SettingsScreen onClose={() => setSettingsOpen(false)} />
      </Modal>

      <AttachMenu
        visible={attachMenuOpen}
        kontekster={byggeKontekster({
          kameraTilladt: true,
          lokationsPraecision: ctxPraecision,
          sidsteFil: pendingAttachments[pendingAttachments.length - 1]?.name,
          udklipHarTekst: ctxUdklip,
          enhedsNavn: enhedsNavn || undefined
        })}
        onKontekst={(slags) => void handleKontekst(slags)}
        onCamera={() => {
          setAttachMenuOpen(false)
          setCameraOpen(true)
        }}
        onGallery={() => void handlePickGallery()}
        onUpload={() => void handlePickDocuments()}
        onPick={(photos) => {
          setAttachMenuOpen(false)
          void stageAttachments(photos)
        }}
        onClose={() => setAttachMenuOpen(false)}
      />

      <Modal visible={sensesOpen} animationType="slide" onRequestClose={() => setSensesOpen(false)}>
        <SensesScreen onClose={() => setSensesOpen(false)} />
      </Modal>

      <Modal visible={artifactsOpen} animationType="slide" onRequestClose={() => setArtifactsOpen(false)}>
        <ArtifactsScreen onClose={() => setArtifactsOpen(false)} />
      </Modal>

      <Modal visible={billederOpen} animationType="slide" onRequestClose={() => setBillederOpen(false)}>
        <BillederScreen
          sessionId={sessions.activeId ?? ''}
          onClose={() => setBillederOpen(false)}
        />
      </Modal>

      <Modal visible={activityOpen} animationType="slide" onRequestClose={() => setActivityOpen(false)}>
        <ActivityCenterScreen
          onClose={() => setActivityOpen(false)}
          runs={activityRuns}
          outboxCount={outboxCount}
          presenceSummary={presence.state}
        />
      </Modal>

      <Modal visible={cameraOpen} animationType="slide" onRequestClose={() => setCameraOpen(false)}>
        <CameraCapture onCapture={handleCapture} onClose={() => setCameraOpen(false)} />
      </Modal>

      <VoiceOverlay
        active={voice.active}
        state={voice.state}
        lastProvider={voice.lastProvider}
        level={voice.level}
        problem={voice.problem}
        interrupt={voice.interrupt}
        workingStep={stream.state.workingStep}
        approval={stream.approval && config ? stream.approval : null}
        onApprove={config ? () => void stream.approve(config) : undefined}
        onDeny={config ? () => void stream.deny(config) : undefined}
        startListening={voice.startListening}
        stopListening={voice.stopListening}
        exit={voice.exit}
        onCameraContext={() => {
          voice.exit()
          setCameraOpen(true)
        }}
      />
    </View>
  )
}

const makestyles = (tokens: Theme) => StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0
  },
  flex: {
    flex: 1
  },
  floatSearch: {
    position: 'absolute',
    left: 0,
    right: 0,
    zIndex: 5
  },
  floatBottom: {
    position: 'absolute',
    left: 0,
    right: 0,
    // Under komponisten ligger enhedens gestus-zone. Uden en bund her
    // lyste en smal stribe tråd igennem dernede — teksten rullede korrekt
    // bagved, men fortsatte forbi den flade der skulle dække den.
    paddingBottom: 16,
    zIndex: 5,
    // Samme halvgennemsigtige flade som TopBar. Uden den lækkede tråden ud
    // NEDEN UNDER komponisten i skærmens sidste par millimeter — teksten
    // rullede korrekt bagved, men fortsatte forbi pillens underkant.
    backgroundColor: tokens.color.scrim
  },
  connBanner: {
    paddingVertical: tokens.spacing.xs,
    alignItems: 'center'
  },
  connOffline: { backgroundColor: tokens.color.error },
  connReconnect: { backgroundColor: tokens.color.warn },
  connText: { color: tokens.color.bg0, fontSize: 12, fontWeight: '700' }
})
