import { useState, useEffect, useRef, type ReactNode } from 'react'
import { UpdateCard } from './components/shell/UpdateCard'
import { DependencyCard } from './components/shell/DependencyCard'
import { useSettings } from './hooks/useSettings'
import { SessionProvider } from './contexts/SessionContext'
import { StreamProvider } from './contexts/StreamContext'
import { PermissionProvider } from './contexts/PermissionContext'
import { usePermission } from './hooks/usePermission'
import { useStream } from './hooks/useStream'
import { AppActionCard } from './components/rich/AppActionCard'
import { resolveAppAction } from './lib/appAction'
import { PanelProvider } from './contexts/PanelContext'
import { UiPanelWatcher } from './components/UiPanelWatcher'
import { AiTransparencyNotice } from './components/AiTransparencyNotice'
import { GlobalShortcuts } from './components/GlobalShortcuts'
import { ApprovalNotifier } from './components/ApprovalNotifier'
import { PresenceHost } from './components/PresenceHost'
import { TakeoverHost } from './components/shell/TakeoverHost'
import { SessionSearch } from './components/SessionSearch'
import { usePanel } from './hooks/usePanel'
import { SplitLayout } from './components/panel/SplitLayout'
import { ArtifactPanel } from './components/panel/ArtifactPanel'
import { useSessions } from './hooks/useSessions'
import { SetupScreen } from './views/SetupScreen'
import { ChatView } from './views/ChatView'
import { CoworkView } from './views/CoworkView'
import { emitZone } from './lib/coworkZone'
import { CodeView } from './views/CodeView'
import { MemoryView } from './views/MemoryView'
import { SchedulingView } from './views/SchedulingView'
import { ImageGalleryView } from './views/ImageGalleryView'
import { Sidebar, type Surface } from './components/shell/Sidebar'
import { StatusBar } from './components/shell/StatusBar'
import './styles/tokens.css'
import './styles/app.css'

/** App = ren wiring. SettingsProvider er wrappet i main.tsx, så useSettings
 *  virker her. Ikke-konfigureret → SetupScreen. Ellers shell med aktiv flade. */
export function App() {
  const { settings, auth, isConfigured, update } = useSettings()
  const [surface, setSurface] = useState<Surface>('chat')

  // Konsolidering (Bjørn 2026-06-21): ÉN settings-flade. Tandhjul/genvej/SecondaryNav
  // navigerede før til en separat SettingsView (dobbelt-truth + ingen scroll). Nu
  // omdirigeres 'settings' instant til cowork-command-centerets Indstillinger-zone,
  // hvor ALLE sektioner bor.
  useEffect(() => {
    if (surface === 'settings') {
      emitZone('settings')
      setSurface('cowork')
    }
  }, [surface])

  if (!settings) return null
  if (!isConfigured) return <SetupScreen onSave={(cfg) => void update(cfg)} />

  const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
  return (
    <SessionProvider config={cfg}>
      <StreamProvider config={cfg}>
        <PermissionProvider>
          <PanelProvider defaultWidth={480}>
            <Shell
              surface={surface}
              setSurface={setSurface}
              role={auth?.role ?? 'guest'}
              userName={auth?.display_name ?? 'Bruger'}
              model={settings.defaultModel}
            />
            <UiPanelWatcher config={cfg} setSurface={setSurface} />
            <AiTransparencyNotice />
            <UpdateHost />
            <DependencyHost />
          </PanelProvider>
        </PermissionProvider>
      </StreamProvider>
    </SessionProvider>
  )
}

interface UpdatesBridge {
  onAvailable: (cb: (i: { version?: string }) => void) => () => void
  onReady: (cb: (i: { version?: string }) => void) => () => void
  download: () => Promise<void>
  install: () => Promise<void>
}
function updatesBridge(): UpdatesBridge | undefined {
  return (window as unknown as { jarvisDesk?: { updates?: UpdatesBridge } }).jarvisDesk?.updates
}

/** Lytter på app-opdaterings-events fra main og viser UpdateCard (§22.5). */
function UpdateHost() {
  const [upd, setUpd] = useState<{ version: string; phase: 'available' | 'ready' } | null>(null)
  // Afvist version huskes, så de 15-min polls ikke nager om SAMME version igen — men en
  // NYERE version (eller 'ready'-fasen efter download) bryder altid igennem (Bjørn 2026-06-23).
  const dismissedRef = useRef<string>('')
  useEffect(() => {
    const u = updatesBridge()
    if (!u) return
    const offA = u.onAvailable((i) => {
      const v = i.version ?? ''
      if (v && v === dismissedRef.current) return  // allerede afvist denne version
      setUpd({ version: v, phase: 'available' })
    })
    const offR = u.onReady((i) => setUpd({ version: i.version ?? '', phase: 'ready' }))
    return () => { offA(); offR() }
  }, [])
  if (!upd) return null
  return (
    <UpdateCard
      version={upd.version}
      phase={upd.phase}
      onUpdate={() => void updatesBridge()?.download()}
      onInstall={() => void updatesBridge()?.install()}
      onDismiss={() => { if (upd.phase === 'available') dismissedRef.current = upd.version; setUpd(null) }}
    />
  )
}

interface DepsBridge {
  detect: () => Promise<{ tool: string; present: boolean }[]>
  install: (tool: string) => Promise<{ ok: boolean; log?: string }>
}
function depsBridge(): DepsBridge | undefined {
  return (window as unknown as { jarvisDesk?: { deps?: DepsBridge } }).jarvisDesk?.deps
}

/** Detekterer manglende værktøjer ved opstart og tilbyder at installere dem. */
function DependencyHost() {
  const [missing, setMissing] = useState<string[]>([])
  const [busy, setBusy] = useState('')
  const [dismissed, setDismissed] = useState(false)
  useEffect(() => {
    const d = depsBridge()
    if (!d) return
    let cancelled = false
    void d.detect().then((tools) => {
      if (!cancelled) setMissing(tools.filter((t) => !t.present).map((t) => t.tool))
    }).catch(() => { /* ignore */ })
    return () => { cancelled = true }
  }, [])
  if (dismissed) return null
  const onInstall = (tool: string) => {
    const d = depsBridge()
    if (!d || busy) return
    setBusy(tool)
    void d.install(tool).then((r) => {
      if (r.ok) setMissing((m) => m.filter((t) => t !== tool))
    }).finally(() => setBusy(''))
  }
  return <DependencyCard missing={missing} onInstall={onInstall} onDismiss={() => setDismissed(true)} busy={busy} />
}

/** Lægger den trækbare split om den aktive view; panel viser det åbne artifact. */
function ShellWithPanel({ children }: { children: ReactNode }) {
  const panel = usePanel()
  const { settings } = useSettings()
  const config = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  return (
    <SplitLayout
      open={panel.open}
      width={panel.width}
      onResize={panel.resize}
      panel={<ArtifactPanel artifact={panel.artifact} onClose={panel.close} config={config} />}
    >
      {children}
    </SplitLayout>
  )
}

function Shell({
  surface,
  setSurface,
  role,
  userName,
  model,
}: {
  surface: Surface
  setSurface: (s: Surface) => void
  role: 'owner' | 'member' | 'guest'
  userName: string
  model: string
}) {
  const { activeId, select } = useSessions()
  const { settings } = useSettings()
  const cfg = settings ? { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken } : undefined
  const [searchOpen, setSearchOpen] = useState(false)
  return (
    <div className="window">
      <Sidebar surface={surface} onSurface={setSurface} userName={userName} />
      <main className="main">
        <ShortcutsHost setSurface={setSurface} onSearch={() => setSearchOpen(true)} />
        <PresenceHost />

        <SessionSearch
          open={searchOpen}
          config={cfg}
          onSelect={(id) => { select(id); setSurface('chat') }}
          onClose={() => setSearchOpen(false)}
        />
        <ApprovalNotifierHost />
        <AppActionHost setSurface={setSurface} />
        <TakeoverHost surface={surface} setSurface={setSurface} />
        <ShellWithPanel>
          {surface === 'chat' && (
            <ChatView
              sessionId={activeId}
              userName={userName}
              onOpenMarketplace={() => { setSurface('cowork'); emitZone('marketplace') }}
              onOpenPrivacy={() => setSurface('settings')}
            />
          )}
          {surface === 'cowork' && <CoworkView role={role} />}
          {surface === 'code' && (
            <CodeView
              sessionId={activeId}
              userName={userName}
              role={role}
              onOpenMarketplace={() => { setSurface('cowork'); emitZone('marketplace') }}
              onOpenPrivacy={() => setSurface('settings')}
            />
          )}
          {surface === 'memory' && <MemoryView role={role} />}
          {surface === 'gallery' && <ImageGalleryView onOpenChat={() => setSurface('chat')} />}
          {surface === 'scheduling' && <SchedulingView role={role} />}
        </ShellWithPanel>
        <StatusBar model={model} sessionId={activeId} />
      </main>
    </div>
  )
}

/** Wirer globale tastaturgenveje med stream-status + surface-skift. */
function ShortcutsHost({ setSurface, onSearch }: { setSurface: (s: Surface) => void; onSearch: () => void }) {
  const stream = useStream()
  return (
    <GlobalShortcuts
      working={stream.status === 'working'}
      onStop={() => { void stream.abort() }}
      onSettings={() => setSurface('settings')}
      onSearch={onSearch}
    />
  )
}

/** Wirer OS-notifikation til afventende godkendelser (Electron gater fokus selv). */
function ApprovalNotifierHost() {
  const stream = useStream()
  const p = stream.pendingApproval
  return (
    <ApprovalNotifier
      approvalId={p?.approvalId ?? null}
      tool={p?.tool}
      action={p?.action}
      notify={(title, body) => {
        const b = (window as unknown as {
          jarvisDesk?: { notifyTaskDone?: (t: string, b: string) => Promise<void> }
        }).jarvisDesk
        void b?.notifyTaskDone?.(title, body)
      }}
    />
  )
}

/** Viser AppActionCard når Jarvis har anmodet om et mode/permission-skift.
 *  Renderes inde i Shell (har adgang til Stream + Permission + setSurface).
 *  Jarvis kan kun ANMODE — kun brugerens klik skifter noget. */
function AppActionHost({ setSurface }: { setSurface: (s: Surface) => void }) {
  const stream = useStream()
  const { setPermission } = usePermission()
  const pending = stream.pendingAppAction
  if (!pending) return null
  return (
    <div className="appaction-host">
      <AppActionCard
        action={pending.action}
        reason={pending.reason}
        onApprove={() => {
          resolveAppAction(
            pending.action,
            {
              setSurface: (s) => setSurface(s),
              setPermission,
              armAutoContinue: stream.armAutoContinue,
            },
            pending.originalMessage,
          )
          stream.clearAppAction()
        }}
        onReject={() => stream.clearAppAction()}
      />
    </div>
  )
}
