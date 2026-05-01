import { useEffect, useState } from 'react'
import { useUnifiedShell } from '@ui/app/useUnifiedShell.js'
import { Sidebar, type ViewKey } from './components/Sidebar'
import { ChatView } from './components/ChatView'
import { MindView } from './components/views/MindView'
import { MemoryView } from './components/views/MemoryView'
import { ToolsView } from './components/views/ToolsView'
import { ClaudeDispatchesView } from './components/views/ClaudeDispatchesView'
import { DashboardView } from './components/views/DashboardView'
import { ChannelsView } from './components/views/ChannelsView'
import { SchedulingView } from './components/views/SchedulingView'
import { SettingsView } from './components/SettingsView'

interface AppConfig {
  apiBaseUrl: string
  userId: string
  userName: string
  mode: 'dev' | 'thin-client' | 'standalone'
  projectRoot: string
  recentProjects: string[]
}

const FALLBACK_CONFIG: AppConfig = {
  apiBaseUrl: 'http://localhost',
  userId: '1246415163603816499', // Bjørn's discord_id from users.json
  userName: 'Bjørn',
  mode: 'dev',
  projectRoot: '',
  recentProjects: [],
}

export default function App() {
  const [view, setView] = useState<ViewKey>('chat')
  const [config, setConfig] = useState<AppConfig>(FALLBACK_CONFIG)
  const [role, setRole] = useState<'owner' | 'member' | 'guest'>('owner')  // optimistic owner; downgraded after whoami fetch

  // Single shell instance shared across views — sessions list lives in
  // Settings (under "Recent chats"), and the active session drives the
  // chat surface. One source of truth, both surfaces stay in sync.
  const shell = useUnifiedShell()

  useEffect(() => {
    if (!window.jarvisx) return
    window.jarvisx.getConfig().then(setConfig).catch(() => undefined)
    // Backend ping subscription kept alive (it still emits events) but
    // we no longer pin its output to a status bar — we removed that.
    // Subscribe to keep the channel warm in case other components want it later.
    const off = window.jarvisx.onBackendStatus(() => undefined)
    return off
  }, [])

  // Resolve role via /api/whoami — drives view-only gating across the
  // app (members can SEE Jarvis's mind but can't unpin or edit settings).
  useEffect(() => {
    fetch(`${config.apiBaseUrl.replace(/\/$/, '')}/api/whoami`)
      .then((r) => r.json())
      .then((j) => {
        const r = j.role
        setRole(r === 'owner' || r === 'member' || r === 'guest' ? r : 'owner')
      })
      .catch(() => setRole('owner'))
  }, [config.apiBaseUrl, config.userId])

  const updateConfig = async (patch: Partial<AppConfig>) => {
    const next = { ...config, ...patch }
    setConfig(next)
    if (window.jarvisx) {
      await window.jarvisx.setConfig(patch)
    }
  }

  // Mirror the active project root to localStorage so apps/ui's Composer
  // (which is shared with webchat) can read it for @file autocomplete
  // without us having to thread props through the embedded ChatPage.
  useEffect(() => {
    try {
      if (config.projectRoot) {
        localStorage.setItem('jarvisx.project_root', config.projectRoot)
      } else {
        localStorage.removeItem('jarvisx.project_root')
      }
    } catch { /* ignore */ }
  }, [config.projectRoot])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <Sidebar
          active={view}
          onSelect={setView}
          userName={config.userName}
          shell={shell}
        />
        <main className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-bg0">
          {view === 'chat' && (
            <ChatView
              apiBaseUrl={config.apiBaseUrl}
              userId={config.userId}
              userName={config.userName}
              projectRoot={config.projectRoot}
              recentProjects={config.recentProjects}
              onProjectChange={updateConfig}
              shell={shell}
              role={role}
            />
          )}
          {view === 'mind' && <MindView apiBaseUrl={config.apiBaseUrl} role={role} />}
          {view === 'memory' && <MemoryView apiBaseUrl={config.apiBaseUrl} />}
          {view === 'tools' && <ToolsView apiBaseUrl={config.apiBaseUrl} />}
          {view === 'dispatches' && <ClaudeDispatchesView apiBaseUrl={config.apiBaseUrl} />}
          {view === 'dashboard' && <DashboardView apiBaseUrl={config.apiBaseUrl} />}
          {view === 'channels' && <ChannelsView apiBaseUrl={config.apiBaseUrl} />}
          {view === 'scheduling' && <SchedulingView apiBaseUrl={config.apiBaseUrl} />}
          {view === 'settings' && (
            <SettingsView config={config} onChange={updateConfig} role={role} />
          )}
        </main>
      </div>
    </div>
  )
}
