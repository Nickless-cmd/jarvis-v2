import { useState, type ReactNode } from 'react'
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
import { SettingsView } from './views/SettingsView'
import { Sidebar, type Surface } from './components/shell/Sidebar'
import { StatusBar } from './components/shell/StatusBar'
import './styles/tokens.css'
import './styles/app.css'

/** App = ren wiring. SettingsProvider er wrappet i main.tsx, så useSettings
 *  virker her. Ikke-konfigureret → SetupScreen. Ellers shell med aktiv flade. */
export function App() {
  const { settings, auth, isConfigured, update } = useSettings()
  const [surface, setSurface] = useState<Surface>('chat')

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
          </PanelProvider>
        </PermissionProvider>
      </StreamProvider>
    </SessionProvider>
  )
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
        <SessionSearch
          open={searchOpen}
          config={cfg}
          onSelect={(id) => { select(id); setSurface('chat') }}
          onClose={() => setSearchOpen(false)}
        />
        <ApprovalNotifierHost />
        <AppActionHost setSurface={setSurface} />
        <ShellWithPanel>
          {surface === 'chat' && (
            <ChatView
              sessionId={activeId}
              userName={userName}
              onOpenMarketplace={() => { setSurface('cowork'); emitZone('marketplace') }}
            />
          )}
          {surface === 'cowork' && <CoworkView role={role} />}
          {surface === 'code' && <CodeView sessionId={activeId} userName={userName} role={role} />}
          {surface === 'memory' && <MemoryView role={role} />}
          {surface === 'gallery' && <ImageGalleryView onOpenChat={() => setSurface('chat')} />}
          {surface === 'scheduling' && <SchedulingView role={role} />}
          {surface === 'settings' && <SettingsView />}
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
