import { useCallback, useEffect, useRef, useState } from 'react'
import { Alert, Animated, AppState, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import notifee, { EventType } from '@notifee/react-native'
import { useKeyboardHeight } from '../lib/useKeyboardHeight'
import { useConnectivity } from '../lib/useConnectivity'
import { ApprovalCard } from '../components/ApprovalCard'
import { Composer } from '../components/Composer'
import { useVoiceConversation } from '../lib/useVoiceConversation'
import { VoiceOverlay } from '../components/VoiceOverlay'
import type { ContentBlock } from '../lib/sseProtocol'
import { ErrorBanner } from '../components/ErrorBanner'
import { ErrorCard } from '../components/ErrorCard'
import { GreetingHero } from '../components/GreetingHero'
import { MessageList, type MessageListHandle } from '../components/MessageList'
import { ScrollToBottom } from '../components/ScrollToBottom'
import { ModelPicker, type ModelChoice } from '../components/ModelPicker'
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
import { cancelActiveRun, getActiveRuns, getModelOptions, uploadAttachment, whoami } from '../lib/apiClient'
import { computeUnread } from '../lib/sessionStatus'
import { loadLastSeen, markSeen } from '../lib/lastSeen'
import { loadLastSession, saveLastSession, loadModelChoice, saveModelChoice } from '../lib/sessionStore'
import { bubble } from '../lib/bubbleModule'
import { submitNotificationReply, REPLY_ACTION_ID } from '../lib/push'
import { useAuth } from '../state/AuthContext'
import { useSessions } from '../state/SessionContext'
import { useStream } from '../state/StreamContext'
import { tokens } from '../theme/tokens'

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
}

export function ChatScreen({ openPanelSignal = 0, syncSignal = 0, onSyncDone }: ChatScreenProps) {
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()
  const [panelOpen, setPanelOpen] = useState(false)

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
  const [cameraOpen, setCameraOpen] = useState(false)
  const [attachMenuOpen, setAttachMenuOpen] = useState(false)
  // FEATURE2/BUG3: valgt/taget billede lægger sig som ventende vedhæftning i
  // composeren (auto-sendes IKKE) så man kan skrive en besked til.
  // FLERE vedhæftninger pr. besked. Med kun én kunne man ikke sende to
  // skærmbilleder sammen — man skulle sende to beskeder, og så mistede Jarvis
  // sammenhængen mellem dem.
  const [pendingAttachments, setPendingAttachments] = useState<
    { id: string; uri: string; name: string; mime: string }[]
  >([])
  const [displayName, setDisplayName] = useState('Jarvis')
  const [modelChoices, setModelChoices] = useState<ModelChoice[]>([])
  const [model, setModel] = useState<ModelChoice | null>(null)
  const [modelPickerOpen, setModelPickerOpen] = useState(false)
  // FEATURE 1: gendan sidst valgte model på tværs af app-genstart. Sættes
  // ubetinget når der findes et gemt valg — whoami-defaulten bruger `cur ??`
  // og bevarer derfor det gemte uanset rækkefølge.
  useEffect(() => {
    void loadModelChoice().then((m) => {
      if (m) setModel(m)
    })
  }, [])
  const connectivity = useConnectivity(config ?? null)
  // Server-side run-status for den aktive session (delt sandhed via /chat/active-
  // runs). Forhindrer at man sender ind i et kørende svar (= nudge-swallow,
  // "han reagerer ikke"), og henter svaret når runnet er færdigt. Matcher
  // Claude/ChatGPT: composeren viser "stop" mens serveren arbejder.
  const [serverBusy, setServerBusy] = useState(false)
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
      if (type === EventType.PRESS) open(detail.notification?.data?.session_id)
      // Direct Reply mens appen er i forgrunden (bruger trækker shade ned).
      if (type === EventType.ACTION_PRESS && detail.pressAction?.id === REPLY_ACTION_ID && config) {
        void submitNotificationReply(config, detail)
      }
    })
    void notifee.getInitialNotification().then((n) => {
      if (!cancelled) open(n?.notification?.data?.session_id)
    })
    return () => {
      cancelled = true
      unsub()
    }
  }, [config])

  useEffect(() => {
    if (!config) return
    sessions.refresh(config).catch(() => undefined)
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
              setModel((cur) => cur ?? OWNER_DEFAULT)
            })
            .catch(() => {
              setModelChoices([OWNER_DEFAULT])
              setModel((cur) => cur ?? OWNER_DEFAULT)
            })
        } else {
          // Member/guest: låst til Standard/Pro.
          setModelChoices(MEMBER_CHOICES)
          setModel((cur) => cur ?? MEMBER_CHOICES[0]!)
        }
      })
      .catch(() => undefined)
    // Gendan den session brugeren sidst var i (åbn samme sted som ved app-luk).
    if (!didRestore.current) {
      didRestore.current = true
      loadLastSession().then((id) => {
        if (id) sessions.select(config, id).catch(() => undefined)
      })
    }
  }, [config])

  // Husk aktiv session på tværs af app-luk.
  useEffect(() => {
    if (sessions.activeId) void saveLastSession(sessions.activeId)
  }, [sessions.activeId])

  // Stream dør når appen baggrunder (Android dræber SSE), men kørslen fortsætter
  // server-side. Når appen kommer tilbage i forgrunden, gen-synkroniserer vi den
  // aktive session så svaret der blev færdigt mens man var væk, dukker op.
  const appStateRef = useRef(AppState.currentState)
  useEffect(() => {
    const sub = AppState.addEventListener('change', (next) => {
      const prev = appStateRef.current
      appStateRef.current = next
      if (prev.match(/inactive|background/) && next === 'active' && config && sessions.activeId) {
        // Gen-synkronisér: A3 lader runnet køre færdigt server-side mens appen er
        // i baggrunden → ved retur henter vi sessionen så det færdige svar vises.
        sessions.select(config, sessions.activeId).catch(() => undefined)
      }
    })
    return () => sub.remove()
  }, [config, sessions.activeId])

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
        const ids = await getActiveRuns(config)
        if (cancelled) return
        const busy = ids.includes(sid)
        const was = serverBusyRef.current
        serverBusyRef.current = busy
        setServerBusy(busy)
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
    const id = setInterval(() => void tick(), 2000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [config, sessions.activeId])

  // Greeting vises når chatten er tom (opstart / ny samtale) — som på desktop.
  const showGreeting = sessions.messages.length === 0 && !sessions.loading

  const modelOpts = () => (model ? { model: model.model, providerChoice: model.providerChoice } : {})

  const ensureSessionAndSend = async (text: string) => {
    if (!config) return
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    const attachmentIds = pendingAttachments.length
      ? pendingAttachments.map((a) => a.id)
      : undefined
    stream.send(config, sessionId, text, { ...modelOpts(), attachmentIds })
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
  })

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
      try {
        const up = await uploadAttachment(config, sessionId, f)
        setPendingAttachments((prev) => [
          ...prev,
          { id: up.id, uri: f.uri, name: f.name, mime: f.mime }
        ])
      } catch (e) {
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
    if (config) sessions.create(config).catch(() => undefined)
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
        <Animated.View style={{ flex: 1, opacity: sessionFade }}>
          {showGreeting ? (
            <GreetingHero userName={displayName} presence={presence} />
          ) : (
            <MessageList
              ref={listRef}
              messages={sessions.messages}
              blocks={stream.state.blocks}
              onResend={(text) => void ensureSessionAndSend(text)}
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
        <Composer
          disabled={!config}
          working={stream.state.status === 'working' || serverBusy}
          modelLabel={model?.label}
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
          onAttach={() => setAttachMenuOpen(true)}
          onMic={voice.enter}
          attachments={pendingAttachments}
          onRemoveAttachment={(id) =>
            setPendingAttachments((prev) => prev.filter((a) => a.id !== id))
          }
          onFocusChange={setComposerFocused}
          showJumpToBottom={scrolledUp && composerFocused}
          onJumpToBottom={jumpToBottom}
        />
        </View>
      </View>

      <ModelPicker
        open={modelPickerOpen}
        choices={modelChoices}
        selectedLabel={model?.label}
        onSelect={(m) => {
          setModel(m)
          void saveModelChoice(m)
        }}
        onClose={() => setModelPickerOpen(false)}
      />

      {config ? (
        <SidePanel
          open={panelOpen}
          onClose={() => setPanelOpen(false)}
          displayName={displayName}
          config={config}
          sessions={sessions.sessions}
          activeId={sessions.activeId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          workingIds={activeRunIds}
          unreadIds={unreadIds}
          isOwner={inHousehold}
          onOpenSenses={() => {
            setPanelOpen(false)
            setSensesOpen(true)
          }}
          onOpenSettings={() => {
            setPanelOpen(false)
            setSettingsOpen(true)
          }}
          bubbleSupported={bubbleSupported}
          onFloatActive={() => {
            const id = sessions.activeId
            if (!id) return
            const title = (sessions.sessions ?? []).find((s) => s.id === id)?.title || 'Jarvis'
            bubble.floatCurrentChat(id, title)
          }}
        />
      ) : null}

      <Modal visible={settingsOpen} animationType="slide" onRequestClose={() => setSettingsOpen(false)}>
        <SettingsScreen onClose={() => setSettingsOpen(false)} />
      </Modal>

      <AttachMenu
        visible={attachMenuOpen}
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

      <Modal visible={cameraOpen} animationType="slide" onRequestClose={() => setCameraOpen(false)}>
        <CameraCapture onCapture={handleCapture} onClose={() => setCameraOpen(false)} />
      </Modal>

      <VoiceOverlay
        active={voice.active}
        state={voice.state}
        mode={voice.mode}
        lastProvider={voice.lastProvider}
        setMode={voice.setMode}
        startListening={voice.startListening}
        stopListening={voice.stopListening}
        exit={voice.exit}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: tokens.color.bg0
  },
  flex: {
    flex: 1
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
    backgroundColor: 'rgba(0,0,0,0.72)'
  },
  connBanner: {
    paddingVertical: tokens.spacing.xs,
    alignItems: 'center'
  },
  connOffline: { backgroundColor: tokens.color.error },
  connReconnect: { backgroundColor: tokens.color.warn },
  connText: { color: tokens.color.bg0, fontSize: 12, fontWeight: '700' }
})
