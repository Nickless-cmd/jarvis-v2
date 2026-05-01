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
import { KeyboardShortcutsOverlay } from './components/KeyboardShortcutsOverlay'
import { OnboardingModal } from './components/OnboardingModal'
import { UpdateBanner } from './components/UpdateBanner'
import { cachedFetch } from './lib/apiCache'
import { matchShortcut, isTypingTarget } from './lib/shortcuts'

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
  const [showShortcuts, setShowShortcuts] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState<boolean>(() => {
    // Show on first launch (no completed flag in localStorage)
    return localStorage.getItem('jarvisx:onboarding-done') !== '1'
  })
  const [sidebarHidden, setSidebarHidden] = useState<boolean>(() => {
    return localStorage.getItem('jarvisx:sidebar-hidden') === '1'
  })
  useEffect(() => {
    localStorage.setItem('jarvisx:sidebar-hidden', sidebarHidden ? '1' : '0')
  }, [sidebarHidden])

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
  // Uses cache-first: cold start with a known last-good value beats
  // the "Loading… / fallback to owner" flash, and offline launches
  // still see the right role.
  useEffect(() => {
    cachedFetch(`${config.apiBaseUrl.replace(/\/$/, '')}/api/whoami`, {
      prefer: 'cache-first',
    })
      .then((r) => r.json())
      .then((j: unknown) => {
        const r = (j as { role?: string }).role
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

  // ── Global keyboard shortcuts ────────────────────────────────
  // Centralized handler for view-switching, sidebar toggle, and
  // shortcut overlay. Per-view shortcuts (Ctrl+K search, Ctrl+/ slash,
  // Ctrl+J terminal, Ctrl+N new chat, Ctrl+L composer) live in their
  // owning components since they need scoped state.
  useEffect(() => {
    const VIEW_BY_DIGIT: Record<number, ViewKey> = {
      1: 'chat',
      2: 'mind',
      3: 'memory',
      4: 'tools',
      5: 'dispatches',
      6: 'dashboard',
      7: 'channels',
      8: 'scheduling',
    }
    const onKey = (e: KeyboardEvent) => {
      // F1 toggles shortcut overlay — works even while typing.
      // (Used to also accept `?` but on Danish/German layouts ? is
      // Shift+-, which collides with regular typing in the composer.
      // F1 is universally safe.)
      if (e.key === 'F1') {
        e.preventDefault()
        setShowShortcuts((v) => !v)
        return
      }
      // The rest of the shortcuts use Ctrl/Cmd, so they don't conflict
      // with normal typing. We still skip when an INPUT element handles
      // the same combo (e.g. browser-native Ctrl+L "open URL bar" is
      // dead in Electron, but be safe with text-edit Ctrl+B in inputs).
      const typing = isTypingTarget(e.target)

      // Ctrl+1..8 → view switch (always works, layout-independent via e.code)
      for (const digit of [1, 2, 3, 4, 5, 6, 7, 8]) {
        if (matchShortcut(e, { ctrl: true, shift: false, alt: false, digit })) {
          e.preventDefault()
          setView(VIEW_BY_DIGIT[digit])
          return
        }
      }
      // Ctrl+, → settings
      if (matchShortcut(e, { ctrl: true, shift: false, alt: false, key: ',' })) {
        e.preventDefault()
        setView('settings')
        return
      }
      // Ctrl+B → toggle sidebar (skip when typing — Ctrl+B is bold in
      // some inputs, though Composer doesn't apply rich-text bold here)
      if (matchShortcut(e, { ctrl: true, shift: false, alt: false, key: 'b' })) {
        if (typing) return
        e.preventDefault()
        setSidebarHidden((v) => !v)
        return
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div className="flex h-full min-h-0 flex-col">
      <UpdateBanner />
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {!sidebarHidden && (
          <Sidebar
            active={view}
            onSelect={setView}
            userName={config.userName}
            shell={shell}
            onShowShortcuts={() => setShowShortcuts(true)}
          />
        )}
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
      <KeyboardShortcutsOverlay
        open={showShortcuts}
        onClose={() => setShowShortcuts(false)}
      />
      <OnboardingModal
        open={showOnboarding}
        apiBaseUrl={config.apiBaseUrl}
        defaultUserName={config.userName}
        onComplete={async (patch) => {
          await updateConfig(patch)
          localStorage.setItem('jarvisx:onboarding-done', '1')
        }}
        onSkip={() => {
          localStorage.setItem('jarvisx:onboarding-done', '1')
          setShowOnboarding(false)
        }}
      />
    </div>
  )
}
