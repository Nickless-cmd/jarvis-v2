import { useCallback, useEffect, useState } from 'react'
import {
  Play,
  Square,
  Plus,
  Trash2,
  CheckCircle2,
  XCircle,
  Loader2,
  Settings as SettingsIcon,
  X,
} from 'lucide-react'

interface TaskDef {
  id: string
  name: string         // user-shown label, also used as process name
  command: string      // shell command to run
}

interface ManagedProcess {
  name: string
  status: 'running' | 'exited' | 'lost' | string
  exit_code?: number | null
  uptime_seconds?: number | null
}

interface Props {
  apiBaseUrl: string
  projectRoot: string
  isOwner: boolean
}

const POLL_MS = 3000

const DEFAULT_TASKS: TaskDef[] = [
  { id: 'test', name: 'test', command: 'npm test' },
  { id: 'build', name: 'build', command: 'npm run build' },
  { id: 'typecheck', name: 'typecheck', command: 'npx tsc --noEmit' },
]

function storageKey(projectRoot: string) {
  return `jarvisx:tasks:${projectRoot || 'global'}`
}

function loadTasks(projectRoot: string): TaskDef[] {
  try {
    const raw = localStorage.getItem(storageKey(projectRoot))
    if (!raw) return DEFAULT_TASKS
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return DEFAULT_TASKS
    return parsed.filter(
      (t): t is TaskDef =>
        t && typeof t.id === 'string' && typeof t.name === 'string' && typeof t.command === 'string',
    )
  } catch {
    return DEFAULT_TASKS
  }
}

function saveTasks(projectRoot: string, tasks: TaskDef[]) {
  localStorage.setItem(storageKey(projectRoot), JSON.stringify(tasks))
}

/**
 * Toolbar of one-click task buttons that spawn via process_supervisor.
 *
 * Each task = name + shell command. List is per-project (keyed by
 * projectRoot) and persisted to localStorage so different repos can
 * have different defaults. The buttons themselves render with status
 * badges:
 *
 *   ▶  idle (no run yet, or last run cleared)
 *   ⟳  running (animated)
 *   ✓  exited cleanly (green)
 *   ✗  exited non-zero (red, with code in tooltip)
 *
 * Clicking a task button:
 *   - if process is running → stop it
 *   - else → spawn it (replace_if_running so a stale "exited" entry
 *            doesn't block a fresh run)
 *
 * The output goes through the existing TerminalDrawer — clicking a
 * task name (vs the play icon) jumps the drawer open to that tab so
 * you can read live output. That's the test/CI surface: structured
 * status pill + one-click drill-down to live tail.
 *
 * Settings cog opens an inline panel for adding/removing/editing tasks.
 */
export function TaskBar({ apiBaseUrl, projectRoot, isOwner }: Props) {
  const [tasks, setTasks] = useState<TaskDef[]>(() => loadTasks(projectRoot))
  const [processes, setProcesses] = useState<Record<string, ManagedProcess>>({})
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const baseUrl = apiBaseUrl.replace(/\/$/, '')

  // Reload tasks when project changes
  useEffect(() => {
    setTasks(loadTasks(projectRoot))
  }, [projectRoot])

  // Persist task changes
  useEffect(() => {
    saveTasks(projectRoot, tasks)
  }, [projectRoot, tasks])

  // Poll the managed-process list to keep status badges fresh
  const refreshProcesses = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/api/processes`)
      if (!res.ok) return
      const j = await res.json()
      const items: ManagedProcess[] = j?.processes || []
      const map: Record<string, ManagedProcess> = {}
      for (const p of items) {
        map[p.name] = p
      }
      setProcesses(map)
    } catch {
      // Silent — task badges just stay stale until next tick
    }
  }, [baseUrl])

  useEffect(() => {
    void refreshProcesses()
    const id = window.setInterval(refreshProcesses, POLL_MS)
    return () => window.clearInterval(id)
  }, [refreshProcesses])

  const runTask = async (task: TaskDef) => {
    if (!isOwner) return
    setBusy(task.id)
    setError(null)
    try {
      const proc = processes[task.name]
      if (proc?.status === 'running') {
        // Stop it
        const res = await fetch(
          `${baseUrl}/api/processes/${encodeURIComponent(task.name)}/stop`,
          { method: 'POST' },
        )
        if (!res.ok) throw new Error(`stop failed: HTTP ${res.status}`)
      } else {
        // Spawn fresh
        const res = await fetch(`${baseUrl}/api/processes`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            name: task.name,
            command: task.command,
            cwd: projectRoot || undefined,
            replace_if_running: true,
          }),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail || `HTTP ${res.status}`)
        }
      }
      void refreshProcesses()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(null)
    }
  }

  const openInTerminal = (taskName: string) => {
    // Make the terminal drawer pop open and select this tab
    window.dispatchEvent(
      new CustomEvent('jarvisx:open-terminal', { detail: { name: taskName } }),
    )
  }

  if (!isOwner && tasks.length === 0) return null

  return (
    <div className="flex flex-shrink-0 flex-wrap items-center gap-1.5 border-b border-line/40 bg-bg1/30 px-4 py-1.5">
      <span className="flex flex-shrink-0 items-center text-[9px] font-semibold uppercase tracking-wider text-fg3">
        Tasks
      </span>
      {tasks.map((task) => {
        const proc = processes[task.name]
        const isBusy = busy === task.id
        const display = renderBadge(proc, isBusy)
        return (
          <div
            key={task.id}
            className={[
              'group flex items-center overflow-hidden rounded-md text-[10px] font-mono ring-1 transition-colors',
              display.cls,
            ].join(' ')}
          >
            <button
              onClick={() => isOwner && runTask(task)}
              disabled={!isOwner || isBusy}
              title={
                proc?.status === 'running'
                  ? `Stop ${task.name}`
                  : `Run ${task.command}`
              }
              className="flex h-5 w-5 flex-shrink-0 items-center justify-center hover:bg-bg0/30 disabled:opacity-50"
            >
              <display.Icon
                size={10}
                className={
                  proc?.status === 'running' || isBusy ? 'animate-spin' : ''
                }
              />
            </button>
            <button
              onClick={() => openInTerminal(task.name)}
              title={`Åbn terminal til ${task.name}`}
              className="flex h-5 items-center px-1.5 pr-2 hover:bg-bg0/30"
            >
              {task.name}
              {proc?.exit_code !== undefined &&
                proc?.exit_code !== null &&
                proc?.status !== 'running' && (
                  <span className="ml-1 opacity-70">{proc.exit_code}</span>
                )}
            </button>
          </div>
        )
      })}
      {isOwner && (
        <button
          onClick={() => setShowSettings((v) => !v)}
          title="Configure tasks"
          className="flex h-5 w-5 flex-shrink-0 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
        >
          <SettingsIcon size={11} />
        </button>
      )}
      {error && (
        <span className="font-mono text-[10px] text-danger">{error}</span>
      )}
      {showSettings && isOwner && (
        <TaskSettings
          projectRoot={projectRoot}
          tasks={tasks}
          onChange={setTasks}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  )
}

function renderBadge(
  proc: ManagedProcess | undefined,
  busy: boolean,
): {
  Icon: typeof Play
  cls: string
} {
  if (busy) {
    return { Icon: Loader2, cls: 'bg-bg2 text-fg3 ring-line2' }
  }
  if (!proc) {
    return { Icon: Play, cls: 'bg-bg2 text-fg3 ring-line2 hover:text-fg' }
  }
  if (proc.status === 'running') {
    return {
      Icon: Square,
      cls: 'bg-accent/15 text-accent ring-accent/30',
    }
  }
  if (proc.status === 'exited') {
    if (proc.exit_code === 0) {
      return { Icon: CheckCircle2, cls: 'bg-ok/15 text-ok ring-ok/30' }
    }
    return { Icon: XCircle, cls: 'bg-danger/15 text-danger ring-danger/30' }
  }
  // 'lost' or unknown
  return { Icon: Play, cls: 'bg-warn/15 text-warn ring-warn/30' }
}

function TaskSettings({
  projectRoot,
  tasks,
  onChange,
  onClose,
}: {
  projectRoot: string
  tasks: TaskDef[]
  onChange: (t: TaskDef[]) => void
  onClose: () => void
}) {
  const [name, setName] = useState('')
  const [command, setCommand] = useState('')
  const valid = name.trim() && command.trim()

  const add = () => {
    if (!valid) return
    onChange([
      ...tasks,
      { id: `t-${Date.now()}`, name: name.trim(), command: command.trim() },
    ])
    setName('')
    setCommand('')
  }
  const remove = (id: string) => onChange(tasks.filter((t) => t.id !== id))

  return (
    <div className="absolute left-4 right-4 top-[140px] z-30 max-w-2xl rounded-md border border-line2 bg-bg1 p-4 shadow-xl">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-[12px] font-semibold">Tasks</h3>
        <button
          onClick={onClose}
          className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
        >
          <X size={12} />
        </button>
      </div>
      <p className="mb-3 text-[10px] text-fg3">
        Per-project · {projectRoot.replace(/^\/home\/[^/]+/, '~') || '(no project)'}
      </p>
      <div className="mb-3 flex flex-col gap-1.5">
        {tasks.map((t) => (
          <div key={t.id} className="flex items-center gap-2 rounded border border-line/60 bg-bg0/40 px-2 py-1.5">
            <span className="w-20 flex-shrink-0 truncate font-mono text-[11px] text-fg2">
              {t.name}
            </span>
            <span className="flex-1 truncate font-mono text-[11px] text-fg3">
              {t.command}
            </span>
            <button
              onClick={() => remove(t.id)}
              className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:text-danger"
            >
              <Trash2 size={10} />
            </button>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          placeholder="navn (fx test)"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="w-32 rounded border border-line bg-bg0 px-2 py-1 font-mono text-[11px] text-fg outline-none focus:border-accent/60"
        />
        <input
          placeholder="kommando (fx pytest -x)"
          value={command}
          onChange={(e) => setCommand(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && valid) add()
          }}
          className="flex-1 rounded border border-line bg-bg0 px-2 py-1 font-mono text-[11px] text-fg outline-none focus:border-accent/60"
        />
        <button
          onClick={add}
          disabled={!valid}
          className="flex items-center gap-1 rounded bg-accent px-2.5 py-1 text-[11px] font-semibold text-bg0 hover:bg-accent/90 disabled:opacity-40"
        >
          <Plus size={10} /> Add
        </button>
      </div>
    </div>
  )
}
