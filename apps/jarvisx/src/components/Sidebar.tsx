import {
  MessageSquare,
  Brain,
  Sparkles,
  Wrench,
  BarChart3,
  Radio,
  Clock,
  Plus,
  Settings as SettingsIcon,
  Workflow,
} from 'lucide-react'
import { SessionList } from './native/SessionList'

export type ViewKey =
  | 'chat'
  | 'mind'
  | 'memory'
  | 'tools'
  | 'dispatches'
  | 'dashboard'
  | 'channels'
  | 'scheduling'
  | 'settings'

interface ShellLike {
  sessions?: unknown[]
  activeSessionId?: string | null
  handleSessionSelect?: (id: string) => void
  handleCreateSession?: () => void
  handleRenameSession?: (id: string, title: string) => void
  handleDeleteSession?: (id: string) => void
}

interface SidebarProps {
  active: ViewKey
  onSelect: (key: ViewKey) => void
  userName: string
  shell?: ShellLike
}

const NAV: { key: ViewKey; label: string; Icon: typeof MessageSquare; hint?: string }[] = [
  { key: 'chat', label: 'Chat', Icon: MessageSquare, hint: 'Samtale med Jarvis' },
  { key: 'mind', label: 'Mind', Icon: Sparkles, hint: 'Hans indre liv: tilstand, drømme, milepæle, identitet' },
  { key: 'memory', label: 'Hukommelse', Icon: Brain, hint: 'Workspace-filer, MEMORY, daily notes' },
  { key: 'tools', label: 'Værktøjer', Icon: Wrench, hint: 'Daemoner og skills' },
  { key: 'dispatches', label: 'Claude jobs', Icon: Workflow, hint: 'Parallelle Claude Code-instanser dispatched af Jarvis' },
  { key: 'dashboard', label: 'Dashboard', Icon: BarChart3, hint: 'CPU, ticks, signal weather' },
  { key: 'channels', label: 'Channels', Icon: Radio, hint: 'Discord, Telegram, WhatsApp' },
  { key: 'scheduling', label: 'Planlægning', Icon: Clock, hint: 'Scheduled tasks & wakeups' },
  { key: 'settings', label: 'Indstillinger', Icon: SettingsIcon, hint: 'Model, providers, tema' },
]

export function Sidebar({ active, onSelect, userName, shell }: SidebarProps) {
  const sessions = Array.isArray(shell?.sessions) ? shell!.sessions : []
  const handleSessionClick = (id: string) => {
    shell?.handleSessionSelect?.(id)
    // Auto-jump to chat view when picking a session — same behaviour as
    // the webchat's AppShell wiring in apps/ui/src/app/App.jsx.
    onSelect('chat')
  }
  return (
    <aside className="flex w-56 flex-col border-r border-line bg-bg1">
      {/* Brand block — ClawX-inspired */}
      <div className="flex items-center gap-3 border-b border-line px-4 py-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-gradient-to-br from-accent to-accent2 font-semibold text-bg0">
          J
        </div>
        <div className="flex flex-col">
          <span className="text-sm font-semibold tracking-tight">JarvisX</span>
          <span className="font-mono text-[10px] text-fg3">{userName}</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-shrink-0 px-2 py-3">
        {NAV.map(({ key, label, Icon, hint }) => {
          const isActive = active === key
          return (
            <div key={key}>
              <button
                onClick={() => onSelect(key)}
                title={hint}
                className={[
                  'group mb-1 flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-bg2 text-fg shadow-inner ring-1 ring-line2'
                    : 'text-fg2 hover:bg-bg2/60 hover:text-fg',
                ].join(' ')}
              >
                <Icon
                  size={16}
                  className={
                    isActive ? 'text-accent' : 'text-fg3 group-hover:text-fg2'
                  }
                />
                <span className="flex-1 text-left">{label}</span>
                {isActive && <span className="h-1.5 w-1.5 rounded-full bg-accent" />}
              </button>
              {/* Sub-item: "Ny chat" indented under Chat — mirrors apps/ui */}
              {key === 'chat' && shell?.handleCreateSession && (
                <button
                  onClick={() => {
                    shell.handleCreateSession?.()
                    onSelect('chat')
                  }}
                  title="Ny chat"
                  className="group mb-1 ml-7 flex w-[calc(100%-1.75rem)] items-center gap-2 rounded-md px-3 py-1.5 text-[12px] text-fg3 transition-colors hover:bg-bg2/60 hover:text-accent"
                >
                  <Plus size={12} className="text-fg3 group-hover:text-accent" />
                  <span>Ny chat</span>
                </button>
              )}
            </div>
          )
        })}
      </nav>

      {/* Recent chats — same component the webchat sidebar uses, mounted
          below the nav items so sessions are always one click away
          regardless of which view you're in. Auto-jumps to Chat on pick. */}
      <div className="flex min-h-0 flex-1 flex-col border-t border-line">
        <div className="flex flex-shrink-0 items-center justify-between px-3 py-2">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-fg3">
            Recent chats
          </span>
          {shell?.handleCreateSession && (
            <button
              onClick={shell.handleCreateSession}
              title="New chat"
              className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-accent"
            >
              <Plus size={11} />
            </button>
          )}
        </div>
        <div className="flex-1 overflow-y-auto">
          {!shell || !Array.isArray(shell.sessions) ? (
            <div className="px-3 py-2 text-[10px] text-fg3">loading…</div>
          ) : (
            <SessionList
              sessions={sessions as { id: string; title: string; updated_at?: string }[]}
              activeSessionId={shell.activeSessionId ?? null}
              onSelect={handleSessionClick}
              onRename={shell.handleRenameSession ?? (() => undefined)}
              onDelete={shell.handleDeleteSession ?? (() => undefined)}
            />
          )}
        </div>
      </div>

      <div className="flex-shrink-0 border-t border-line px-4 py-2 text-[10px] text-fg3">
        v0.1.0-poc
      </div>
    </aside>
  )
}
