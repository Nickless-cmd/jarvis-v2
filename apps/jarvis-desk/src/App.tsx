import { useState, type ReactNode } from 'react'
import { useSettings } from './hooks/useSettings'
import { SessionProvider } from './contexts/SessionContext'
import { StreamProvider } from './contexts/StreamContext'
import { PanelProvider } from './contexts/PanelContext'
import { usePanel } from './hooks/usePanel'
import { SplitLayout } from './components/panel/SplitLayout'
import { ArtifactPanel } from './components/panel/ArtifactPanel'
import { useSessions } from './hooks/useSessions'
import { SetupScreen } from './views/SetupScreen'
import { ChatView } from './views/ChatView'
import { CoworkView } from './views/CoworkView'
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
        <PanelProvider defaultWidth={480}>
          <Shell
            surface={surface}
            setSurface={setSurface}
            role={auth?.role ?? 'guest'}
            userName={auth?.display_name ?? 'Bruger'}
            model={settings.defaultModel}
          />
        </PanelProvider>
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
  const { activeId } = useSessions()
  return (
    <div className="window">
      <Sidebar surface={surface} onSurface={setSurface} userName={userName} />
      <main className="main">
        <ShellWithPanel>
          {surface === 'chat' && <ChatView sessionId={activeId} />}
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
