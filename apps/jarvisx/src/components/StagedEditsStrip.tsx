import { useEffect, useState, useCallback } from 'react'
import {
  GitBranch,
  Check,
  X,
  ChevronDown,
  ChevronUp,
  AlertCircle,
  FileEdit,
  FilePlus,
} from 'lucide-react'

interface StagedEdit {
  stage_id: string
  kind: 'edit_file' | 'write_file'
  path: string
  staged_at: string
  additions: number
  deletions: number
  file_existed: boolean
  note?: string
  diff?: string
}

interface StagedListResp {
  session_id: string
  count: number
  edits: StagedEdit[]
  updated_at: string
}

interface CommitResp {
  status: string
  committed_count?: number
  remaining_staged?: number
  results?: Array<{ stage_id: string; path: string; status: string }>
  error?: { stage_id: string; path: string; error: string }
}

interface Props {
  apiBaseUrl: string
  sessionId: string | null
}

/**
 * Strip above the chat that surfaces staged edits — paths, +/- counts,
 * expandable to show full unified diffs, with Commit / Discard buttons.
 *
 * The "Why a UI for it" answer: Jarvis can already commit/discard via
 * the tools, but a human-in-the-loop button means Bjørn can preview a
 * batch before letting it land — the whole point of the stage primitive.
 */
export function StagedEditsStrip({ apiBaseUrl, sessionId }: Props) {
  const [data, setData] = useState<StagedListResp | null>(null)
  const [expanded, setExpanded] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStaged = useCallback(async () => {
    if (!sessionId) return
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/staged-edits?session_id=${encodeURIComponent(
        sessionId,
      )}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = (await res.json()) as StagedListResp
      setData(j)
    } catch (e: unknown) {
      // Silent — the strip just stays hidden if the endpoint is unreachable
      setData(null)
    }
  }, [apiBaseUrl, sessionId])

  // Poll every 3s — staged edits are bursty, picked up shortly after
  // Jarvis stages, but not so often we hammer the API.
  useEffect(() => {
    fetchStaged()
    const id = window.setInterval(fetchStaged, 3000)
    return () => window.clearInterval(id)
  }, [fetchStaged])

  const commit = async (stageIds?: string[]) => {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/staged-edits/commit?session_id=${encodeURIComponent(
        sessionId,
      )}`
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stageIds ?? null),
      })
      const j = (await res.json()) as CommitResp
      if (j.status !== 'ok') {
        setError(
          j.error
            ? `${j.error.path}: ${j.error.error}`
            : `commit returned ${j.status}`,
        )
      }
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      void fetchStaged()
    }
  }

  const discard = async (stageIds?: string[]) => {
    if (!sessionId) return
    if (!stageIds && !confirm('Drop all staged edits?')) return
    setBusy(true)
    setError(null)
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/staged-edits/discard?session_id=${encodeURIComponent(
        sessionId,
      )}`
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(stageIds ?? null),
      })
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      void fetchStaged()
    }
  }

  if (!data || data.count === 0) return null

  const totals = data.edits.reduce(
    (acc, e) => ({ adds: acc.adds + e.additions, dels: acc.dels + e.deletions }),
    { adds: 0, dels: 0 },
  )

  return (
    <div className="flex flex-shrink-0 flex-col border-b border-warn/30 bg-warn/5">
      <div className="flex items-center gap-3 px-4 py-2">
        <GitBranch size={12} className="flex-shrink-0 text-warn" />
        <span className="flex-shrink-0 text-[10px] font-semibold uppercase tracking-wider text-warn">
          Staged · {data.count}
        </span>
        <span className="flex-shrink-0 font-mono text-[10px]">
          <span className="text-ok">+{totals.adds}</span>
          <span className="mx-1 text-fg3">·</span>
          <span className="text-danger">−{totals.dels}</span>
        </span>
        <button
          onClick={() => setExpanded((e) => !e)}
          className="flex flex-1 items-center gap-1 truncate text-left text-[11px] text-fg2 hover:text-fg"
        >
          {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          <span className="font-mono opacity-70">
            {data.edits.map((e) => shortPath(e.path)).slice(0, 3).join(', ')}
            {data.edits.length > 3 && ` +${data.edits.length - 3} more`}
          </span>
        </button>
        <button
          onClick={() => discard()}
          disabled={busy}
          title="Discard all staged edits"
          className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-2.5 py-1 text-[10px] text-fg2 hover:border-danger/40 hover:text-danger disabled:opacity-50"
        >
          <X size={10} /> Discard
        </button>
        <button
          onClick={() => commit()}
          disabled={busy}
          title="Apply all staged edits"
          className="flex items-center gap-1.5 rounded-md bg-ok px-2.5 py-1 text-[10px] font-semibold text-bg0 hover:bg-ok/90 disabled:opacity-50"
        >
          <Check size={10} /> Apply all
        </button>
      </div>

      {error && (
        <div className="flex items-start gap-2 border-t border-warn/20 bg-danger/10 px-4 py-1.5">
          <AlertCircle size={11} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[10px] text-danger">{error}</span>
        </div>
      )}

      {expanded && (
        <div className="max-h-[420px] overflow-y-auto border-t border-warn/20 bg-bg0/60 px-4 py-2">
          {data.edits.map((e) => (
            <StagedEditCard
              key={e.stage_id}
              edit={e}
              onCommit={() => commit([e.stage_id])}
              onDiscard={() => discard([e.stage_id])}
              busy={busy}
            />
          ))}
        </div>
      )}
    </div>
  )
}

function StagedEditCard({
  edit,
  onCommit,
  onDiscard,
  busy,
}: {
  edit: StagedEdit
  onCommit: () => void
  onDiscard: () => void
  busy: boolean
}) {
  const Icon = edit.kind === 'edit_file' ? FileEdit : FilePlus
  return (
    <div className="mb-2 rounded-md border border-line bg-bg1 last:mb-0">
      <div className="flex items-center gap-2 border-b border-line/60 px-3 py-1.5">
        <Icon size={11} className="flex-shrink-0 text-warn" />
        <span className="flex-1 truncate font-mono text-[11px] text-fg">
          {edit.path}
        </span>
        <span className="flex-shrink-0 font-mono text-[10px]">
          <span className="text-ok">+{edit.additions}</span>
          <span className="mx-1 text-fg3">·</span>
          <span className="text-danger">−{edit.deletions}</span>
        </span>
        <button
          onClick={onDiscard}
          disabled={busy}
          title="Discard"
          className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-danger"
        >
          <X size={10} />
        </button>
        <button
          onClick={onCommit}
          disabled={busy}
          title="Apply only this"
          className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-ok"
        >
          <Check size={10} />
        </button>
      </div>
      {edit.diff && <DiffBlock diff={edit.diff} />}
    </div>
  )
}

function DiffBlock({ diff }: { diff: string }) {
  const lines = diff.split('\n')
  return (
    <div className="font-mono text-[11px] leading-snug">
      {lines.map((line, i) => {
        let cls = 'diff-context'
        let bg = ''
        let color = '#c9d1d9'
        if (line.startsWith('+++ ') || line.startsWith('--- ')) {
          color = '#6e7681'
        } else if (line.startsWith('+')) {
          cls = 'diff-add'
          bg = 'rgba(63,185,80,.10)'
          color = '#7fdb8b'
        } else if (line.startsWith('-')) {
          cls = 'diff-del'
          bg = 'rgba(248,81,73,.10)'
          color = '#ff7b72'
        } else if (line.startsWith('@@')) {
          cls = 'diff-hunk'
          bg = 'rgba(88,166,255,.08)'
          color = '#79c0ff'
        }
        return (
          <div
            key={i}
            className={cls}
            style={{
              display: 'flex',
              background: bg,
              padding: '0 8px',
              whiteSpace: 'pre',
            }}
          >
            <span
              style={{
                width: '1.2em',
                color: '#6e7681',
                opacity: 0.5,
                flexShrink: 0,
                textAlign: 'center',
              }}
            >
              {line[0] || ' '}
            </span>
            <span style={{ color, flex: 1 }}>
              {line.slice(line.startsWith('+++') || line.startsWith('---') ? 0 : 1)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function shortPath(path: string): string {
  return path.replace(/^\/home\/[^/]+/, '~').split('/').slice(-2).join('/')
}
