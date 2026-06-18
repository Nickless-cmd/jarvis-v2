import { useEffect, useRef, useState } from 'react'
import { Alert, AppState, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { useKeyboardHeight } from '../lib/useKeyboardHeight'
import { useConnectivity } from '../lib/useConnectivity'
import { ApprovalCard } from '../components/ApprovalCard'
import { Composer } from '../components/Composer'
import { ConnectionPill } from '../components/ConnectionPill'
import { ErrorBanner } from '../components/ErrorBanner'
import { GreetingHero } from '../components/GreetingHero'
import { LivenessRing } from '../components/LivenessRing'
import { MessageList } from '../components/MessageList'
import { ModelPicker, type ModelChoice } from '../components/ModelPicker'
import { SidePanel } from '../components/SidePanel'
import { SettingsScreen } from './SettingsScreen'
import { CameraCapture, type CapturedPhoto } from './CameraCapture'
import { getModelOptions, uploadAttachment, whoami } from '../lib/apiClient'
import { loadLastSession, saveLastSession } from '../lib/sessionStore'
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
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [cameraOpen, setCameraOpen] = useState(false)
  const [displayName, setDisplayName] = useState('Jarvis')
  const [modelChoices, setModelChoices] = useState<ModelChoice[]>([])
  const [model, setModel] = useState<ModelChoice | null>(null)
  const [modelPickerOpen, setModelPickerOpen] = useState(false)
  const connectivity = useConnectivity(config ?? null)
  const keyboardHeight = useKeyboardHeight()
  // Løft composeren op over tastaturet med fuld tastaturhøjde. (Tidligere
  // trak vi insets.bottom fra, men keyboardHeight inkluderer allerede
  // navigationslinjen i edge-to-edge → det dobbelt-fratrak og lod composeren
  // ligge lidt skjult. Fuld højde sikrer den altid er fri af tastaturet.)
  const liftPadding = keyboardHeight

  const didRestore = useRef(false)

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
        sessions.select(config, sessions.activeId).catch(() => undefined)
        // Re-attach til sessionens live-stream (delte sessioner): fanger et run
        // op der stadig kører (vores eget der overlevede baggrunden via A3, eller
        // en anden enhed/Jarvis der skriver netop nu).
        stream.follow(config, sessions.activeId)
      }
    })
    return () => sub.remove()
  }, [config, sessions.activeId])

  // Delte sessioner: følg den aktive sessions live-stream, så transcript +
  // liveness (pulserende ring + "arbejder") vises live uanset HVEM der skriver —
  // anden enhed eller Jarvis autonomt. Bygger på broadcast-bufferen (A1/A3).
  useEffect(() => {
    if (!config || !sessions.activeId) return
    stream.follow(config, sessions.activeId)
    return () => stream.stopFollow()
  }, [config, sessions.activeId])

  // Greeting vises når chatten er tom (opstart / ny samtale) — som på desktop.
  const showGreeting = sessions.messages.length === 0 && !sessions.loading

  const modelOpts = () => (model ? { model: model.model, providerChoice: model.providerChoice } : {})

  const ensureSessionAndSend = async (text: string) => {
    if (!config) return
    const sessionId = sessions.activeId ?? (await sessions.create(config)).id
    stream.send(config, sessionId, text, modelOpts())
  }

  // In-app kamera → upload billede → send med beskeden (multimodal).
  const handleCapture = async (photo: CapturedPhoto) => {
    setCameraOpen(false)
    if (!config) return
    try {
      const sessionId = sessions.activeId ?? (await sessions.create(config)).id
      const up = await uploadAttachment(config, sessionId, photo)
      stream.send(config, sessionId, '📷 Billede', { ...modelOpts(), attachmentIds: [up.id] })
    } catch {
      Alert.alert('Billede', 'Kunne ikke uploade billedet — prøv igen.')
    }
  }

  const handleSelectSession = (sessionId: string) => {
    setPanelOpen(false)
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
              stream.state.status === 'working'
                ? 'working'
                : stream.state.status === 'error'
                  ? 'error'
                  : 'idle'
            }
          />
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
      ) : null}

      <View style={[styles.flex, { paddingBottom: liftPadding }]}>
        {showGreeting ? (
          <GreetingHero userName={displayName} />
        ) : (
          <MessageList
            messages={sessions.messages}
            blocks={stream.state.blocks}
            onResend={(text) => void ensureSessionAndSend(text)}
          />
        )}
        {canRetry ? (
          <ErrorBanner
            title={stream.state.status === 'error' ? 'Stream fejlede' : 'Svar stoppet'}
            detail="Du kan prøve den seneste besked igen."
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
        <Composer
          disabled={!config}
          working={stream.state.status === 'working'}
          modelLabel={model?.label}
          onSend={ensureSessionAndSend}
          onStop={() => (config ? stream.stop(config) : undefined)}
          onPressModel={() => setModelPickerOpen(true)}
          onAttach={() => setCameraOpen(true)}
          onMic={() => Alert.alert('Stemme', 'Diktering kommer i næste opdatering.')}
        />
      </View>

      <ModelPicker
        open={modelPickerOpen}
        choices={modelChoices}
        selectedLabel={model?.label}
        onSelect={setModel}
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
          onOpenSettings={() => {
            setPanelOpen(false)
            setSettingsOpen(true)
          }}
        />
      ) : null}

      <Modal visible={settingsOpen} animationType="slide" onRequestClose={() => setSettingsOpen(false)}>
        <SettingsScreen onClose={() => setSettingsOpen(false)} />
      </Modal>

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
