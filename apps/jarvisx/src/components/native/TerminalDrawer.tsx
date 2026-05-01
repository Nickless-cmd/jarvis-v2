import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Terminal, X, Square, RotateCw, ChevronDown, Trash2 } from 'lucide-react'
import { AnsiText } from '@ui/components/chat/AnsiText.jsx'

interface ManagedProcess {
  name: string
  pid: number
  status: 'running' | 'exited' | 'lost' | string
  command?: string
  cwd?: string
  started_at?: string
  uptime_seconds?: number | null
  exit_code?: number | null
  stopped_at?: string | null
  log_path?: string
}

interface Props {
  open: boolean
  onClose: () => void
  apiBaseUrl: string
  role: 'owner' | 'member' | 'guest'
}

const POLL_LIST_MS = 4000
const POLL_LOG_MS = 1500
const DEFAULT_HEIGHT = 280
const MIN_HEIGHT = 120
const MAX_HEIGHT_FRAC = 0.7  // 70% of viewport at most

/**
 * Bottom-drawer terminal panel. Polls the JarvisX API for managed
 * processes (those Jarvis spawned via process_supervisor) and shows
 * their live log output in tabbed panes.
 *
 * UX notes:
 *   - Resizable via top-edge drag handle, persisted to localStorage.
 *   - Active tab polls log at 1.5s; list polls at 4s.
 *   - Auto-scrolls to bottom on new content unless the user has
 *     scrolled up (then it leaves them alone — same convention as
 *     the message list).
 *   - Owner-only actions: stop (SIGTERM+grace+SIGKILL) and remove
 *     (delete from registry once exited). Members see read-only.
 *   - Falls back to a friendly empty state when no processes exist.
 *
 * Why not WebSocket / SSE? Polling is dead simple, the load is
 * trivial (a tail-the-last-N-lines call), and we sidestep proxy /
 * connection-lifecycle bugs. Can be upgraded later if needed.
 */
export function TerminalDrawer({ open, onClose, apiBaseUrl, role }: Props) {
  const [processes, setProcesses] = useState<ManagedProcess[]>([])
  const [activeName, setActiveName] = useState<string | null>(null)
  const [log, setLog] = useState<string>('')
  const [logLoading, setLogLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [height, setHeight] = useState<number>(() => {
    const stored = Number(localStorage.getItem('jarvisx:terminal-height'))
    return stored && stored >= MIN_HEIGHT ? stored : DEFAULT_HEIGHT
  })
  const logRef = useRef<HTMLDivElement>(null)
  const wasNearBottomRef = useRef(true)
  const dragStartRef = useRef<{ y: number; h: number } | null>(null)

  // ── Cross-app channel: TaskBar dispatches `jarvisx:open-terminal`
  // with { detail: { name } } to jump straight to that process tab.
  // Drawer-open is handled upstream in ChatView.
  useEffect(() => {
    const onOpen = (e: Event) => {
      const detail = (e as CustomEvent<{ name?: string }>).detail
      if (detail?.name) setActiveName(detail.name)
    }
    window.addEventListener('jarvisx:open-terminal', onOpen)
    return () => window.removeEventListener('jarvisx:open-terminal', onOpen)
  }, [])

  // ── Polling: list of processes ─────────────────────────────────
  const refreshList = useCallback(async () => {
    try {
      const res = await fetch(`${apiBaseUrl}/api/processes`)
      if (!res.ok) throw new Error(`list failed: HTTP ${res.status}`)
      const data = await res.json()
      const items: ManagedProcess[] = data?.processes || []
      setProcesses(items)
      // Auto-pick first running process if none selected
      if (!activeName && items.length > 0) {
        const firstRunning = items.find((p) => p.status === 'running') || items[0]
        setActiveName(firstRunning.name)
      }
      // If active was removed externally, reset
      if (activeName && !items.some((p) => p.name === activeName)) {
        setActiveName(items[0]?.name ?? null)
      }
    } catch (e) {
      // Silent — we'll surface the next log fetch error if persistent
      console.warn('[TerminalDrawer] list refresh failed:', e)
    }
  }, [apiBaseUrl, activeName])

  useEffect(() => {
    if (!open) return
    void refreshList()
    const id = window.setInterval(refreshList, POLL_LIST_MS)
    return () => window.clearInterval(id)
  }, [open, refreshList])

  // ── Polling: active log tail ───────────────────────────────────
  useEffect(() => {
    if (!open || !activeName) {
      setLog('')
      return
    }
    let cancelled = false
    const fetchLog = async () => {
      try {
        if (!log) setLogLoading(true)
        const res = await fetch(
          `${apiBaseUrl}/api/processes/${encodeURIComponent(activeName)}/log?lines=500`,
        )
        if (!res.ok) throw new Error(`log failed: HTTP ${res.status}`)
        const data = await res.json()
        if (cancelled) return
        setLog(data?.lines ?? '')
        setError(null)
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (!cancelled) setLogLoading(false)
      }
    }
    void fetchLog()
    const id = window.setInterval(fetchLog, POLL_LOG_MS)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, activeName, apiBaseUrl])

  // ── Auto-scroll to bottom on new content if user is near bottom
  useEffect(() => {
    const node = logRef.current
    if (!node) return
    if (wasNearBottomRef.current) {
      node.scrollTop = node.scrollHeight
    }
  }, [log])

  const onLogScroll = () => {
    const node = logRef.current
    if (!node) return
    const distance = node.scrollHeight - node.scrollTop - node.clientHeight
    wasNearBottomRef.current = distance < 60
  }

  // ── Resize via top drag handle ─────────────────────────────────
  const onDragStart = (e: React.PointerEvent) => {
    e.preventDefault()
    dragStartRef.current = { y: e.clientY, h: height }
    document.addEventListener('pointermove', onDragMove)
    document.addEventListener('pointerup', onDragEnd, { once: true })
  }
  const onDragMove = (e: PointerEvent) => {
    const start = dragStartRef.current
    if (!start) return
    const delta = start.y - e.clientY  // up = grow
    const next = Math.max(
      MIN_HEIGHT,
      Math.min(window.innerHeight * MAX_HEIGHT_FRAC, start.h + delta),
    )
    setHeight(next)
  }
  const onDragEnd = () => {
    dragStartRef.current = null
    document.removeEventListener('pointermove', onDragMove)
    localStorage.setItem('jarvisx:terminal-height', String(Math.round(height)))
  }
  // Persist any time height settles (covers programmatic changes too)
  useEffect(() => {
    localStorage.setItem('jarvisx:terminal-height', String(Math.round(height)))
  }, [height])

  // ── Owner actions ──────────────────────────────────────────────
  const stopProcess = async (name: string) => {
    if (role !== 'owner') return
    try {
      const res = await fetch(
        `${apiBaseUrl}/api/processes/${encodeURIComponent(name)}/stop`,
        { method: 'POST' },
      )
      if (!res.ok) throw new Error(`stop failed: HTTP ${res.status}`)
      void refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }
  const removeProcess = async (name: string) => {
    if (role !== 'owner') return
    try {
      const res = await fetch(
        `${apiBaseUrl}/api/processes/${encodeURIComponent(name)}`,
        { method: 'DELETE' },
      )
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || `remove failed: HTTP ${res.status}`)
      }
      if (activeName === name) setActiveName(null)
      void refreshList()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    }
  }

  const active = useMemo(
    () => processes.find((p) => p.name === activeName) ?? null,
    [processes, activeName],
  )

  if (!open) return null

  return (
    <div
      className="flex flex-shrink-0 flex-col border-t border-line bg-bg0"
      style={{ height }}
    >
      {/* Drag handle */}
      <div
        onPointerDown={onDragStart}
        className="group flex h-1.5 flex-shrink-0 cursor-ns-resize items-center justify-center bg-bg1 hover:bg-accent/30"
        title="Træk for at ændre højde"
      >
        <div className="h-0.5 w-12 rounded bg-line group-hover:bg-accent" />
      </div>

      {/* Tab strip + close */}
      <div className="flex flex-shrink-0 items-center border-b border-line bg-bg1">
        <div className="flex flex-1 items-center overflow-x-auto">
          <div className="flex flex-shrink-0 items-center gap-1.5 px-3 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg3">
            <Terminal size={11} />
            Terminal
          </div>
          {processes.length === 0 ? (
            <span className="px-2 py-1.5 text-[11px] italic text-fg3">
              ingen kørende processer
            </span>
          ) : (
            processes.map((p) => {
              const isActive = p.name === activeName
              return (
                <button
                  key={p.name}
                  onClick={() => setActiveName(p.name)}
                  className={[
                    'flex items-center gap-1.5 border-r border-line/60 px-3 py-1.5 text-[11px] font-mono transition-colors',
                    isActive
                      ? 'bg-bg0 text-fg ring-1 ring-inset ring-accent/30'
                      : 'text-fg2 hover:bg-bg2/60 hover:text-fg',
                  ].join(' ')}
                  title={p.command}
                >
                  <span
                    className={[
                      'h-1.5 w-1.5 flex-shrink-0 rounded-full',
                      p.status === 'running'
                        ? 'animate-pulse bg-accent'
                        : p.status === 'exited'
                        ? 'bg-fg3'
                        : 'bg-warn',
                    ].join(' ')}
                  />
                  <span className="max-w-[160px] truncate">{p.name}</span>
                  {p.status !== 'running' && p.exit_code !== null && p.exit_code !== undefined && (
                    <span
                      className={[
                        'rounded px-1 text-[9px]',
                        p.exit_code === 0 ? 'text-fg3' : 'text-danger',
                      ].join(' ')}
                    >
                      exit {p.exit_code}
                    </span>
                  )}
                </button>
              )
            })
          )}
        </div>
        <div className="flex flex-shrink-0 items-center gap-1 border-l border-line/60 px-2 py-1">
          <button
            onClick={() => void refreshList()}
            title="Genindlæs"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <RotateCw size={12} />
          </button>
          <button
            onClick={onClose}
            title="Skjul terminal (Ctrl+J)"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <ChevronDown size={14} />
          </button>
        </div>
      </div>

      {/* Active process meta + actions */}
      {active && (
        <div className="flex flex-shrink-0 items-center justify-between border-b border-line/40 bg-bg1/50 px-3 py-1 text-[10px] font-mono text-fg3">
          <div className="flex min-w-0 items-center gap-3">
            <span className="truncate" title={active.command}>
              {active.command}
            </span>
            {active.cwd && (
              <span className="hidden truncate text-fg3/70 md:inline" title={active.cwd}>
                {active.cwd.replace(/^\/home\/[^/]+/, '~')}
              </span>
            )}
            <span className="flex-shrink-0">pid {active.pid}</span>
            {active.uptime_seconds !== null && active.uptime_seconds !== undefined && (
              <span className="flex-shrink-0">
                {formatUptime(active.uptime_seconds)}
              </span>
            )}
          </div>
          {role === 'owner' && (
            <div className="flex flex-shrink-0 items-center gap-1">
              {active.status === 'running' ? (
                <button
                  onClick={() => stopProcess(active.name)}
                  title="Stop process (SIGTERM, SIGKILL efter grace)"
                  className="flex items-center gap-1 rounded px-1.5 py-0.5 text-fg3 hover:bg-danger/15 hover:text-danger"
                >
                  <Square size={10} />
                  stop
                </button>
              ) : (
                <button
                  onClick={() => removeProcess(active.name)}
                  title="Fjern fra registry"
                  className="flex items-center gap-1 rounded px-1.5 py-0.5 text-fg3 hover:bg-danger/15 hover:text-danger"
                >
                  <Trash2 size={10} />
                  fjern
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Log viewport */}
      <div
        ref={logRef}
        onScroll={onLogScroll}
        className="flex-1 overflow-auto bg-bg0 p-3 font-mono text-[11px] leading-relaxed text-fg2"
        style={{ scrollBehavior: 'auto' }}
      >
        {error && (
          <div className="mb-2 rounded border border-danger/30 bg-danger/10 px-2 py-1 text-[10px] text-danger">
            {error}
          </div>
        )}
        {!active && processes.length === 0 && (
          <div className="flex h-full items-center justify-center text-center text-[11px] text-fg3">
            <div>
              <Terminal size={20} className="mx-auto mb-2 opacity-40" />
              <div>Ingen kørende processer</div>
              <div className="mt-1 text-fg3/70">
                Når Jarvis spawner via <code>process_spawn</code> dukker de op her.
              </div>
            </div>
          </div>
        )}
        {active && !log && logLoading && (
          <div className="text-fg3 italic">indlæser log…</div>
        )}
        {active && log && (
          <pre className="whitespace-pre-wrap break-words">
            <AnsiText text={log} className="" />
          </pre>
        )}
        {active && !log && !logLoading && !error && (
          <div className="text-fg3 italic">log er tom</div>
        )}
      </div>

      {/* Footer (close affordance for very small heights) */}
      <button
        onClick={onClose}
        title="Skjul (Ctrl+J)"
        className="absolute right-2 top-2 hidden"
      >
        <X size={12} />
      </button>
    </div>
  )
}

function formatUptime(seconds: number): string {
  const s = Math.floor(seconds)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  const h = Math.floor(m / 60)
  return `${h}t ${m % 60}m`
}
