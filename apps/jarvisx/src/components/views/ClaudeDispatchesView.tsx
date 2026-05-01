import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  Workflow,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  Clock,
  GitBranch,
  Cpu,
  RefreshCw,
} from 'lucide-react'

interface Dispatch {
  task_id: string
  status: 'running' | 'success' | 'failed' | 'budget_exceeded' | string
  started_at: string
  ended_at: string | null
  elapsed_seconds: number | null
  tokens_used: number
  exit_code: number | null
  diff_summary: string | null
  error: string | null
  prompt: string
  branch: string
  model?: string
  max_turns?: number
  allowed_paths?: string[]
}

interface BudgetSnapshot {
  hour_bucket: string
  dispatches_used: number
  dispatches_max: number
  tokens_used: number
  tokens_max: number
}

interface DiffResp {
  task_id: string
  status: string
  worktree_alive: boolean
  diff: string
  diff_summary: string | null
}

interface Props {
  apiBaseUrl: string
}

const POLL_LIST_MS = 3000
const POLL_DIFF_MS = 2500

/**
 * "Claude jobs" view — live dashboard for parallel Claude Code
 * instances Jarvis has dispatched via the dispatch_to_claude_code
 * tool. Without this view, those dispatches are a black box: Jarvis
 * fires them, they run for minutes in isolation, you have no idea
 * what they're doing or how far they've gotten.
 *
 * Layout: budget bar → list (left) → detail+live-diff (right).
 * Polling updates list at 3s, active diff at 2.5s. Running tasks
 * sort to the top, finished by started_at desc.
 */
export function ClaudeDispatchesView({ apiBaseUrl }: Props) {
  const [dispatches, setDispatches] = useState<Dispatch[]>([])
  const [budget, setBudget] = useState<BudgetSnapshot | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [diff, setDiff] = useState<DiffResp | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const baseUrl = apiBaseUrl.replace(/\/$/, '')

  const refresh = useCallback(async () => {
    try {
      setLoading(true)
      const [listRes, budgetRes] = await Promise.all([
        fetch(`${baseUrl}/api/dispatches?limit=100`),
        fetch(`${baseUrl}/api/dispatches/budget`),
      ])
      if (!listRes.ok) throw new Error(`list failed: HTTP ${listRes.status}`)
      const listData = await listRes.json()
      const items: Dispatch[] = listData?.dispatches || []
      setDispatches(items)
      if (budgetRes.ok) setBudget(await budgetRes.json())
      // Auto-select first running, else first overall
      setActiveId((current) => {
        if (current && items.some((d) => d.task_id === current)) return current
        const firstRunning = items.find((d) => d.status === 'running')
        return firstRunning?.task_id ?? items[0]?.task_id ?? null
      })
      setError(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [baseUrl])

  useEffect(() => {
    void refresh()
    const id = window.setInterval(refresh, POLL_LIST_MS)
    return () => window.clearInterval(id)
  }, [refresh])

  // Poll the active dispatch's diff (only while running — finished
  // dispatches' worktrees are cleaned up so we just keep last fetched)
  useEffect(() => {
    if (!activeId) {
      setDiff(null)
      return
    }
    let cancelled = false
    const fetchDiff = async () => {
      try {
        const res = await fetch(
          `${baseUrl}/api/dispatches/${encodeURIComponent(activeId)}/diff`,
        )
        if (!res.ok) throw new Error(`diff failed: HTTP ${res.status}`)
        const j = (await res.json()) as DiffResp
        if (!cancelled) setDiff(j)
      } catch {
        // Silent — diff isn't critical, list-level error is enough
      }
    }
    void fetchDiff()
    const active = dispatches.find((d) => d.task_id === activeId)
    if (active?.status === 'running') {
      const id = window.setInterval(fetchDiff, POLL_DIFF_MS)
      return () => {
        cancelled = true
        window.clearInterval(id)
      }
    }
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, dispatches.find((d) => d.task_id === activeId)?.status, baseUrl])

  const active = useMemo(
    () => dispatches.find((d) => d.task_id === activeId) ?? null,
    [dispatches, activeId],
  )

  const runningCount = dispatches.filter((d) => d.status === 'running').length

  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden bg-bg0">
      {/* Header + budget */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex items-center gap-3">
          <Workflow size={14} className="text-accent" />
          <h2 className="text-sm font-semibold">Claude jobs</h2>
          {runningCount > 0 && (
            <span className="flex items-center gap-1 rounded-full bg-accent/15 px-2 py-0.5 text-[10px] font-semibold text-accent">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-accent" />
              {runningCount} kører
            </span>
          )}
          <span className="text-[10px] text-fg3">
            Parallelle Claude Code-instanser Jarvis har dispatched
          </span>
        </div>
        <button
          onClick={() => void refresh()}
          title="Genindlæs"
          disabled={loading}
          className="flex h-7 w-7 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg disabled:opacity-50"
        >
          {loading ? (
            <Loader2 size={12} className="animate-spin" />
          ) : (
            <RefreshCw size={12} />
          )}
        </button>
      </header>

      {budget && <BudgetBar b={budget} />}

      {error && (
        <div className="flex flex-shrink-0 items-start gap-2 border-b border-danger/30 bg-danger/10 px-4 py-2">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[11px] text-danger">{error}</span>
        </div>
      )}

      {/* Body: list + detail */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        <aside className="flex w-[340px] flex-shrink-0 flex-col overflow-hidden border-r border-line bg-bg1">
          <div className="flex flex-shrink-0 items-center justify-between border-b border-line/60 px-3 py-2">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-fg3">
              {dispatches.length} dispatch{dispatches.length === 1 ? '' : 'es'}
            </span>
          </div>
          <div className="flex-1 overflow-y-auto">
            {dispatches.length === 0 ? (
              <div className="flex h-full items-center justify-center text-center text-[11px] text-fg3">
                <div className="px-4">
                  <Workflow size={24} className="mx-auto mb-2 opacity-30" />
                  <div>Ingen dispatches endnu</div>
                  <div className="mt-1 text-fg3/70">
                    Når Jarvis bruger <code>dispatch_to_claude_code</code>{' '}
                    dukker de op her.
                  </div>
                </div>
              </div>
            ) : (
              dispatches.map((d) => (
                <DispatchRow
                  key={d.task_id}
                  d={d}
                  active={d.task_id === activeId}
                  onSelect={() => setActiveId(d.task_id)}
                />
              ))
            )}
          </div>
        </aside>

        <section className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {active ? (
            <DispatchDetail dispatch={active} diff={diff} />
          ) : (
            <div className="flex flex-1 items-center justify-center text-center text-[11px] text-fg3">
              <div>
                <Workflow size={28} className="mx-auto mb-2 opacity-30" />
                <div>Vælg en dispatch i listen</div>
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function BudgetBar({ b }: { b: BudgetSnapshot }) {
  const dispatchPct = (b.dispatches_used / b.dispatches_max) * 100
  const tokenPct = (b.tokens_used / b.tokens_max) * 100
  const dispatchClose = dispatchPct >= 80
  const tokenClose = tokenPct >= 80
  return (
    <div className="flex flex-shrink-0 items-center gap-4 border-b border-line/60 bg-bg1/40 px-4 py-2 font-mono text-[10px]">
      <span className="text-fg3 uppercase tracking-wider">budget /h</span>
      <div className="flex items-center gap-2">
        <span className={dispatchClose ? 'text-warn' : 'text-fg2'}>
          {b.dispatches_used}/{b.dispatches_max} dispatches
        </span>
        <div className="h-1 w-24 overflow-hidden rounded-full bg-bg2">
          <div
            className={[
              'h-full transition-all',
              dispatchClose ? 'bg-warn' : 'bg-accent',
            ].join(' ')}
            style={{ width: `${Math.min(100, dispatchPct)}%` }}
          />
        </div>
      </div>
      <div className="flex items-center gap-2">
        <span className={tokenClose ? 'text-warn' : 'text-fg2'}>
          {Math.round(b.tokens_used / 1000)}k/{Math.round(b.tokens_max / 1000)}k tokens
        </span>
        <div className="h-1 w-24 overflow-hidden rounded-full bg-bg2">
          <div
            className={[
              'h-full transition-all',
              tokenClose ? 'bg-warn' : 'bg-accent',
            ].join(' ')}
            style={{ width: `${Math.min(100, tokenPct)}%` }}
          />
        </div>
      </div>
      <span className="text-fg3">{b.hour_bucket}</span>
    </div>
  )
}

function DispatchRow({
  d,
  active,
  onSelect,
}: {
  d: Dispatch
  active: boolean
  onSelect: () => void
}) {
  return (
    <div
      onClick={onSelect}
      className={[
        'cursor-pointer border-b border-line/30 px-3 py-2 text-[11px] transition-colors',
        active ? 'bg-bg2 text-fg' : 'text-fg2 hover:bg-bg2/40',
      ].join(' ')}
    >
      <div className="flex items-center gap-2">
        <StatusBadge status={d.status} />
        <span className="flex-1 truncate font-mono text-[10px] text-fg3" title={d.task_id}>
          {d.task_id}
        </span>
        {d.elapsed_seconds !== null && (
          <span className="flex-shrink-0 font-mono text-[9px] text-fg3">
            {formatElapsed(d.elapsed_seconds)}
          </span>
        )}
      </div>
      {d.prompt && (
        <div className="mt-1 line-clamp-2 text-[11px] leading-snug">
          {d.prompt}
        </div>
      )}
      <div className="mt-1 flex items-center gap-3 font-mono text-[9px] text-fg3">
        {d.tokens_used > 0 && <span>{d.tokens_used.toLocaleString()} tokens</span>}
        {d.model && <span title="Model">{d.model}</span>}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string; Icon: typeof Loader2 }> = {
    running: { label: 'kører', cls: 'bg-accent/15 text-accent ring-accent/30', Icon: Loader2 },
    success: { label: 'success', cls: 'bg-ok/15 text-ok ring-ok/30', Icon: CheckCircle2 },
    failed: { label: 'failed', cls: 'bg-danger/15 text-danger ring-danger/30', Icon: AlertTriangle },
    budget_exceeded: { label: 'budget', cls: 'bg-warn/15 text-warn ring-warn/30', Icon: AlertTriangle },
  }
  const meta = map[status] ?? {
    label: status,
    cls: 'bg-bg2 text-fg3 ring-line2',
    Icon: Clock,
  }
  return (
    <span
      className={[
        'flex flex-shrink-0 items-center gap-1 rounded-full px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider ring-1',
        meta.cls,
      ].join(' ')}
    >
      <meta.Icon
        size={9}
        className={status === 'running' ? 'animate-spin' : ''}
      />
      {meta.label}
    </span>
  )
}

function DispatchDetail({
  dispatch: d,
  diff,
}: {
  dispatch: Dispatch
  diff: DiffResp | null
}) {
  return (
    <>
      <div className="flex flex-shrink-0 items-center justify-between border-b border-line/60 bg-bg1/40 px-4 py-2">
        <div className="flex min-w-0 flex-1 items-center gap-3">
          <StatusBadge status={d.status} />
          <span className="truncate font-mono text-[11px] text-fg" title={d.task_id}>
            {d.task_id}
          </span>
          <span className="flex flex-shrink-0 items-center gap-1 font-mono text-[10px] text-fg3">
            <GitBranch size={10} />
            {d.branch}
          </span>
        </div>
        <div className="flex flex-shrink-0 items-center gap-3 font-mono text-[10px] text-fg3">
          {d.elapsed_seconds !== null && (
            <span className="flex items-center gap-1">
              <Clock size={10} />
              {formatElapsed(d.elapsed_seconds)}
            </span>
          )}
          <span className="flex items-center gap-1">
            <Cpu size={10} />
            {d.tokens_used.toLocaleString()} tokens
          </span>
          {d.model && <span title="Model">{d.model}</span>}
          {d.exit_code !== null && d.exit_code !== undefined && (
            <span className={d.exit_code === 0 ? 'text-fg3' : 'text-danger'}>
              exit {d.exit_code}
            </span>
          )}
        </div>
      </div>

      {/* Spec */}
      <div className="flex-shrink-0 border-b border-line/40 bg-bg1/20 px-4 py-3">
        <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-fg3">
          Prompt
        </div>
        <div className="whitespace-pre-wrap break-words text-[12px] leading-relaxed text-fg2">
          {d.prompt || '(empty prompt)'}
        </div>
        {(d.allowed_paths && d.allowed_paths.length > 0) || d.max_turns ? (
          <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] text-fg3">
            {d.max_turns && (
              <span className="font-mono">max_turns: {d.max_turns}</span>
            )}
            {d.allowed_paths?.map((p) => (
              <span
                key={p}
                className="rounded bg-bg2 px-1.5 py-0.5 font-mono text-fg2"
                title={p}
              >
                {p}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      {/* Error */}
      {d.error && (
        <div className="flex flex-shrink-0 items-start gap-2 border-b border-danger/30 bg-danger/10 px-4 py-2">
          <AlertTriangle size={12} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="whitespace-pre-wrap font-mono text-[11px] text-danger">
            {d.error}
          </span>
        </div>
      )}

      {/* Live diff or final summary */}
      <div className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-line/40 bg-bg1/30 px-4 py-1.5 text-[10px] font-semibold uppercase tracking-wider text-fg3">
          {d.status === 'running' ? 'live diff' : 'final diff'}
          {diff && diff.worktree_alive && (
            <span className="flex items-center gap-1 rounded bg-accent/15 px-1.5 py-0.5 text-[9px] text-accent">
              <span className="h-1 w-1 animate-pulse rounded-full bg-accent" />
              worktree alive
            </span>
          )}
        </div>
        <div className="flex-1 overflow-auto bg-bg0 p-3 font-mono text-[11px] leading-relaxed">
          {diff && diff.diff ? (
            <DiffBody diff={diff.diff} />
          ) : d.diff_summary ? (
            <div className="text-fg2">
              <div className="mb-2 text-[10px] uppercase tracking-wider text-fg3">
                Summary
              </div>
              <pre className="whitespace-pre-wrap break-words">{d.diff_summary}</pre>
            </div>
          ) : (
            <div className="italic text-fg3">
              {d.status === 'running'
                ? 'Indlæser diff…'
                : 'Worktree ryddet op — ingen diff tilgængelig'}
            </div>
          )}
        </div>
      </div>
    </>
  )
}

/** Minimal unified diff renderer — reuses the styling from DiffReviewPanel. */
function DiffBody({ diff }: { diff: string }) {
  const lines = diff.split('\n')
  return (
    <div>
      {lines.map((line, i) => {
        let kind: 'add' | 'del' | 'hunk' | 'meta' | 'ctx' = 'ctx'
        if (line.startsWith('diff ') || line.startsWith('index ') || line.startsWith('+++') || line.startsWith('---')) {
          kind = 'meta'
        } else if (line.startsWith('@@')) kind = 'hunk'
        else if (line.startsWith('+')) kind = 'add'
        else if (line.startsWith('-')) kind = 'del'

        const bg =
          kind === 'add'
            ? 'rgba(63,185,80,.10)'
            : kind === 'del'
            ? 'rgba(248,81,73,.10)'
            : kind === 'hunk'
            ? 'rgba(88,166,255,.08)'
            : kind === 'meta'
            ? 'rgba(110,118,129,.06)'
            : 'transparent'
        const fg =
          kind === 'add'
            ? '#7fdb8b'
            : kind === 'del'
            ? '#ff7b72'
            : kind === 'hunk'
            ? '#79c0ff'
            : kind === 'meta'
            ? '#8b929c'
            : '#c9d1d9'
        return (
          <div
            key={i}
            style={{
              display: 'block',
              background: bg,
              color: fg,
              padding: '0 8px',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
            }}
          >
            {line || '\u00A0'}
          </div>
        )
      })}
    </div>
  )
}

function formatElapsed(seconds: number): string {
  const s = Math.floor(seconds)
  if (s < 60) return `${s}s`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m}m ${s % 60}s`
  const h = Math.floor(m / 60)
  return `${h}t ${m % 60}m`
}
