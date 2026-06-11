import { useState } from 'react'
import { useSettings } from './hooks/useSettings'
import { SessionProvider } from './contexts/SessionContext'
import { StreamProvider } from './contexts/StreamContext'
import { useSessions } from './hooks/useSessions'
import { SetupScreen } from './views/SetupScreen'
import { ChatView } from './views/ChatView'
import { CoworkView } from './views/CoworkView'
import { CodeView } from './views/CodeView'
import { MemoryView } from './views/MemoryView'
import { SchedulingView } from './views/SchedulingView'
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
        <Shell
          surface={surface}
          setSurface={setSurface}
          role={auth?.role ?? 'guest'}
          userName={auth?.display_name ?? 'Bruger'}
          model={settings.defaultModel}
        />
      </StreamProvider>
    </SessionProvider>
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
        {surface === 'chat' && (activeId ? <ChatView sessionId={activeId} /> : <EmptyChat />)}
        {surface === 'cowork' && <CoworkView />}
        {surface === 'code' && <CodeView />}
        {surface === 'memory' && <MemoryView role={role} />}
        {surface === 'scheduling' && <SchedulingView role={role} />}
        {surface === 'settings' && <SettingsView />}
        <StatusBar model={model} sessionId={activeId} />
      </main>
    </div>
  )
}

function EmptyChat() {
  return (
    <div className="empty-state">
      <div>
        <h2>Hej.</h2>
        <div>Vælg en samtale eller start en ny.</div>
      </div>
    </div>
  )
}
