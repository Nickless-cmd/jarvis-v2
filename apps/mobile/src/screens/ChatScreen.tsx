import { useEffect, useRef, useState } from 'react'
import { Alert, Animated, AppState, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import notifee, { EventType } from '@notifee/react-native'
import { useKeyboardHeight } from '../lib/useKeyboardHeight'
import { useConnectivity } from '../lib/useConnectivity'
import { ApprovalCard } from '../components/ApprovalCard'
import { Composer } from '../components/Composer'
import { StreamIndicator } from '../components/StreamIndicator'
import { ConnectionPill } from '../components/ConnectionPill'
import { ErrorBanner } from '../components/ErrorBanner'
import { GreetingHero } from '../components/GreetingHero'
import { LivenessRing } from '../components/LivenessRing'
import { MessageList, type MessageListHandle } from '../components/MessageList'
import { SaveRail } from '../components/SaveRail'
import { ModelPicker, type ModelChoice } from '../components/ModelPicker'
import { SidePanel } from '../components/SidePanel'
import { SettingsScreen } from './SettingsScreen'
import { CameraCapture, type CapturedPhoto } from './CameraCapture'
import { AttachMenu } from '../components/AttachMenu'
import { pickImageFromGallery } from '../lib/imagePicker'
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

export function ChatScreen() {
  const { config } = useAuth()
  const sessions = useSessions()
  const stream = useStream()
  const [panelOpen, setPanelOpen] = useState(false)
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
  // Save Rail: skjult som standard, vises ved scroll-aktivitet, gemmer sig efter
  // ~2,8s uden aktivitet (lang nok til at man kan ramme knapperne; rail-tryk/scrub
  // scroller selv → nulstiller timeren).
  const [railVisible, setRailVisible] = useState(false)
  // Chatboble: kun vis "flyt til boble"-knap hvis enheden understøtter Bubbles API.
  const [bubbleSupported, setBubbleSupported] = useState(false)
  useEffect(() => { void bubble.isSupported().then(setBubbleSupported) }, [])
  const railTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const bumpRail = () => {
    setRailVisible(true)
    if (railTimer.current) clearTimeout(railTimer.current)
    railTimer.current = setTimeout(() => setRailVisible(false), 2800)
  }
  useEffect(() => () => { if (railTimer.current) clearTimeout(railTimer.current) }, [])
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [attachMenuOpen, setAttachMenuOpen] = useState(false)
  // FEATURE2/BUG3: valgt/taget billede lægger sig som ventende vedhæftning i
  // composeren (auto-sendes IKKE) så man kan skrive en besked til.
  const [pendingAttachment, setPendingAttachment] = useState<{ id: string; uri: string; name: string } | null>(null)
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
    const attachmentIds = pendingAttachment ? [pendingAttachment.id] : undefined
    stream.send(config, sessionId, text, { ...modelOpts(), attachmentIds })
    setPendingAttachment(null)
  }

  // Upload billede (kamera/galleri) → stage som ventende vedhæftning i composeren
  // (BUG3: ikke auto-send). Sendes når brugeren trykker send, med valgfri besked.
  const stageAttachment = async (photo: CapturedPhoto) => {
    if (!config) return
    try {
      const sessionId = sessions.activeId ?? (await sessions.create(config)).id
      const up = await uploadAttachment(config, sessionId, photo)
      setPendingAttachment({ id: up.id, uri: photo.uri, name: photo.name })
    } catch {
      Alert.alert('Billede', 'Kunne ikke uploade billedet — prøv igen.')
    }
  }

  const handleCapture = async (photo: CapturedPhoto) => {
    setCameraOpen(false)
    await stageAttachment(photo)
  }

  const handlePickGallery = async () => {
    setAttachMenuOpen(false)
    const photo = await pickImageFromGallery()
    if (photo) await stageAttachment(photo)
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

  return (
    <View style={styles.root}>
      <View style={styles.header}>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Åbn sessioner og plugins"
          onPress={() => setPanelOpen((open) => !open)}
          style={styles.headerTitle}
          hitSlop={8}
        >
          <LivenessRing
            status={
              stream.state.status === 'working' || serverBusy
                ? 'working'
                : stream.state.status === 'error'
                  ? 'error'
                  : 'idle'
            }
          />
          {activeRunIds.length > 0 || Object.values(unreadIds).some(Boolean) ? (
            <View style={styles.ringBadge} />
          ) : null}
          <Text style={styles.title} numberOfLines={1}>
            {displayName}
          </Text>
        </Pressable>
        <ConnectionPill label={stream.state.status} />
      </View>

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

      <View style={[styles.flex, { paddingBottom: liftPadding }]}>
        <Animated.View style={{ flex: 1, opacity: sessionFade }}>
          {showGreeting ? (
            <GreetingHero userName={displayName} />
          ) : (
            <MessageList
              ref={listRef}
              messages={sessions.messages}
              blocks={stream.state.blocks}
              onResend={(text) => void ensureSessionAndSend(text)}
              onScrollActivity={bumpRail}
            />
          )}
        </Animated.View>
        {!showGreeting ? (
          <SaveRail
            visible={railVisible && sessions.messages.length >= 2}
            onJumpTop={() => listRef.current?.jumpTop()}
            onJumpBottom={() => listRef.current?.jumpBottom()}
            onOlderUser={() => listRef.current?.jumpOlderUser()}
            onNewerUser={() => listRef.current?.jumpNewerUser()}
            onScrub={(f) => listRef.current?.scrubTo(f)}
          />
        ) : null}
        {canRetry ? (
          <ErrorBanner
            title={stream.state.status === 'error' ? 'Stream fejlede' : 'Svar stoppet'}
            detail={
              stream.state.status === 'error' && stream.lastError
                ? `Årsag: ${stream.lastError}`
                : 'Du kan prøve den seneste besked igen.'
            }
            actionLabel="Retry"
            onAction={() => void ensureSessionAndSend(lastUserMessage.content)}
          />
        ) : null}
        {stream.approval && config ? (
          <ApprovalCard
            approval={stream.approval}
            onApprove={() => void stream.approve(config)}
            onDeny={() => void stream.deny(config)}
          />
        ) : null}
        <StreamIndicator active={stream.state.status === 'working' || serverBusy} />
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
          onMic={() => Alert.alert('Stemme', 'Diktering kommer i næste opdatering.')}
          attachment={pendingAttachment ? { uri: pendingAttachment.uri, name: pendingAttachment.name } : null}
          onRemoveAttachment={() => setPendingAttachment(null)}
        />
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
          sessions={sessions.sessions}
          activeId={sessions.activeId}
          onSelectSession={handleSelectSession}
          onNewSession={handleNewSession}
          workingIds={activeRunIds}
          unreadIds={unreadIds}
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
        onClose={() => setAttachMenuOpen(false)}
      />

      <Modal visible={cameraOpen} animationType="slide" onRequestClose={() => setCameraOpen(false)}>
        <CameraCapture onCapture={handleCapture} onClose={() => setCameraOpen(false)} />
      </Modal>
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
  header: {
    height: 56,
    paddingHorizontal: tokens.spacing.md,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderBottomColor: tokens.color.line,
    borderBottomWidth: 1
  },
  headerTitle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: tokens.spacing.sm,
    flexShrink: 1
  },
  ringBadge: {
    position: 'absolute',
    top: 0,
    left: 18,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: tokens.color.accent
  },
  title: {
    color: tokens.color.fg1,
    fontSize: 18,
    fontWeight: '700',
    flexShrink: 1
  },
  connBanner: {
    paddingVertical: tokens.spacing.xs,
    alignItems: 'center'
  },
  connOffline: { backgroundColor: tokens.color.error },
  connReconnect: { backgroundColor: tokens.color.warn },
  connText: { color: tokens.color.bg0, fontSize: 12, fontWeight: '700' }
})
