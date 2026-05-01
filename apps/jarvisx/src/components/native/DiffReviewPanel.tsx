import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  X,
  Check,
  GitBranch,
  FileEdit,
  FilePlus,
  AlertCircle,
  Loader2,
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
  open: boolean
  onClose: () => void
}

/**
 * Full-panel diff review for staged edits — the Claude Code superpower.
 *
 * The strip above the chat is a glance; this is the focused review mode
 * you open before letting a batch land. Layout:
 *
 *   ┌───────────────────────────────────────────────────────┐
 *   │  Review staged edits · +X −Y     [Discard]  [Apply]   │
 *   ├───────────────┬───────────────────────────────────────┤
 *   │ File list     │ Active file: path                     │
 *   │  - foo.py +12 │   @@ -10,3 +10,5 @@                   │
 *   │ ▸ bar.ts +3   │  ctx                                  │
 *   │  - baz.md +1  │ + add                                 │
 *   │               │ - del                                 │
 *   │               │ ...                                   │
 *   └───────────────┴───────────────────────────────────────┘
 *
 * Mounts as a modal-ish overlay that fills the main chat area (sidebar
 * stays visible). Esc closes; clicking outside doesn't — review is a
 * deliberate activity, not a flyout.
 *
 * v1 limitations (deliberate):
 *   - No per-hunk accept/reject (file-level only). Per-hunk needs
 *     round-tripping edited diffs back through stage_edit, which is a
 *     real refactor of the staging primitive — saving for v2.
 *   - Unified diff only (no side-by-side). The diffs are pre-computed
 *     by the backend; rendering them as side-by-side from a unified
 *     payload is doable but adds parser complexity for limited gain
 *     when most edits are small. Can revisit when we see big diffs.
 *   - No syntax highlighting inside diff lines. Adding Prism on top of
 *     diff coloring is fiddly (the line prefix throws off tokenization).
 *     Plain monospace + add/del/hunk colors is the proven readable form.
 */
export function DiffReviewPanel({ apiBaseUrl, sessionId, open, onClose }: Props) {
  const [data, setData] = useState<StagedListResp | null>(null)
  const [loading, setLoading] = useState(false)
  const [activeStageId, setActiveStageId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchStaged = useCallback(async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const url = `${apiBaseUrl.replace(/\/$/, '')}/api/staged-edits?session_id=${encodeURIComponent(
        sessionId,
      )}`
      const res = await fetch(url)
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const j = (await res.json()) as StagedListResp
      setData(j)
      // Preserve active selection if still present, else jump to first
      setActiveStageId((current) => {
        if (current && j.edits.some((e) => e.stage_id === current)) return current
        return j.edits[0]?.stage_id ?? null
      })
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }, [apiBaseUrl, sessionId])

  // Refresh on open + every 4s while open (slower than the strip — when
  // you're reviewing, sudden changes are jarring; the strip is the
  // realtime indicator).
  useEffect(() => {
    if (!open) return
    void fetchStaged()
    const id = window.setInterval(fetchStaged, 4000)
    return () => window.clearInterval(id)
  }, [open, fetchStaged])

  // Esc closes (but only when not busy committing/discarding)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !busy) {
        e.preventDefault()
        onClose()
      }
    }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open, busy, onClose])

  const commit = async (stageIds?: string[]) => {
    if (!sessionId) return
    setBusy(true)
    setError(null)
    try {
      const res = await fetch(
        `${apiBaseUrl.replace(/\/$/, '')}/api/staged-edits/commit?session_id=${encodeURIComponent(sessionId)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(stageIds ?? null),
        },
      )
      const j = (await res.json()) as CommitResp
      if (j.status !== 'ok') {
        setError(
          j.error
            ? `${j.error.path}: ${j.error.error}`
            : `commit returned ${j.status}`,
        )
      } else {
        // If we just committed everything, close the panel
        await fetchStaged()
        if ((j.remaining_staged ?? 0) === 0) {
          onClose()
        }
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
      void fetchStaged()
    }
  }

  const discard = async (stageIds?: string[]) => {
    if (!sessionId) return
    if (!stageIds && !confirm('Drop alle staged edits?')) return
    setBusy(true)
    setError(null)
    try {
      await fetch(
        `${apiBaseUrl.replace(/\/$/, '')}/api/staged-edits/discard?session_id=${encodeURIComponent(sessionId)}`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(stageIds ?? null),
        },
      )
      await fetchStaged()
      // If we just dropped everything, close the panel
      if (!stageIds) onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setBusy(false)
    }
  }

  const totals = useMemo(() => {
    if (!data) return { adds: 0, dels: 0 }
    return data.edits.reduce(
      (acc, e) => ({ adds: acc.adds + e.additions, dels: acc.dels + e.deletions }),
      { adds: 0, dels: 0 },
    )
  }, [data])

  const active = useMemo(
    () => data?.edits.find((e) => e.stage_id === activeStageId) ?? null,
    [data, activeStageId],
  )

  if (!open) return null

  return (
    <div className="absolute inset-0 z-30 flex flex-col bg-bg0">
      {/* Header */}
      <header className="flex flex-shrink-0 items-center justify-between border-b border-line bg-bg1 px-4 py-2">
        <div className="flex min-w-0 items-center gap-3">
          <GitBranch size={14} className="flex-shrink-0 text-warn" />
          <h2 className="flex-shrink-0 text-sm font-semibold">Review staged edits</h2>
          {data && data.count > 0 && (
            <span className="flex-shrink-0 font-mono text-[11px]">
              <span className="text-fg3">{data.count} fil{data.count === 1 ? '' : 'er'}</span>
              <span className="mx-2 text-fg3">·</span>
              <span className="text-ok">+{totals.adds}</span>
              <span className="mx-1 text-fg3">·</span>
              <span className="text-danger">−{totals.dels}</span>
            </span>
          )}
          {loading && <Loader2 size={12} className="animate-spin text-fg3" />}
        </div>
        <div className="flex flex-shrink-0 items-center gap-2">
          {data && data.count > 0 && (
            <>
              <button
                onClick={() => discard()}
                disabled={busy}
                title="Drop alle staged edits"
                className="flex items-center gap-1.5 rounded-md border border-line2 bg-bg2 px-3 py-1.5 text-[11px] text-fg2 hover:border-danger/40 hover:text-danger disabled:opacity-50"
              >
                <X size={11} /> Discard alle
              </button>
              <button
                onClick={() => commit()}
                disabled={busy}
                title="Apply alle staged edits"
                className="flex items-center gap-1.5 rounded-md bg-ok px-3 py-1.5 text-[11px] font-semibold text-bg0 hover:bg-ok/90 disabled:opacity-50"
              >
                <Check size={11} /> Apply alle
              </button>
            </>
          )}
          <button
            onClick={() => !busy && onClose()}
            disabled={busy}
            title="Luk (Esc)"
            className="flex h-7 w-7 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg disabled:opacity-50"
          >
            <X size={14} />
          </button>
        </div>
      </header>

      {error && (
        <div className="flex flex-shrink-0 items-start gap-2 border-b border-danger/30 bg-danger/10 px-4 py-2">
          <AlertCircle size={12} className="mt-0.5 flex-shrink-0 text-danger" />
          <span className="font-mono text-[11px] text-danger">{error}</span>
        </div>
      )}

      {/* Body */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* File list */}
        <aside className="flex w-[280px] flex-shrink-0 flex-col overflow-hidden border-r border-line bg-bg1">
          <div className="flex flex-shrink-0 items-center gap-2 border-b border-line/60 px-3 py-2 text-[10px] font-semibold uppercase tracking-wider text-fg3">
            Filer
          </div>
          <div className="flex-1 overflow-y-auto">
            {!data || data.count === 0 ? (
              <div className="px-3 py-6 text-center text-[11px] text-fg3">
                Ingen staged edits
              </div>
            ) : (
              data.edits.map((e) => (
                <FileRow
                  key={e.stage_id}
                  edit={e}
                  active={e.stage_id === activeStageId}
                  onSelect={() => setActiveStageId(e.stage_id)}
                  onDiscard={() => discard([e.stage_id])}
                  onApply={() => commit([e.stage_id])}
                  busy={busy}
                />
              ))
            )}
          </div>
        </aside>

        {/* Diff viewport */}
        <section className="flex min-w-0 flex-1 flex-col overflow-hidden">
          {active ? (
            <>
              <div className="flex flex-shrink-0 items-center justify-between border-b border-line/60 bg-bg1/50 px-4 py-2">
                <div className="flex min-w-0 items-center gap-2">
                  {active.kind === 'edit_file' ? (
                    <FileEdit size={12} className="flex-shrink-0 text-warn" />
                  ) : (
                    <FilePlus size={12} className="flex-shrink-0 text-ok" />
                  )}
                  <span
                    className="truncate font-mono text-[12px] text-fg"
                    title={active.path}
                  >
                    {active.path}
                  </span>
                  {!active.file_existed && (
                    <span className="flex-shrink-0 rounded bg-ok/15 px-1.5 py-0.5 text-[9px] font-semibold uppercase text-ok">
                      ny
                    </span>
                  )}
                </div>
                <div className="flex flex-shrink-0 items-center gap-3 font-mono text-[10px]">
                  <span className="text-ok">+{active.additions}</span>
                  <span className="text-danger">−{active.deletions}</span>
                  <span className="text-fg3">·</span>
                  <span className="text-fg3">{active.kind}</span>
                </div>
              </div>
              {active.note && (
                <div className="flex-shrink-0 border-b border-line/40 bg-bg1/30 px-4 py-1.5 text-[11px] italic text-fg3">
                  {active.note}
                </div>
              )}
              <div className="flex-1 overflow-auto bg-bg0">
                {active.diff ? (
                  <DiffBody diff={active.diff} />
                ) : (
                  <div className="px-4 py-6 text-[11px] text-fg3">
                    Ingen diff data — backend returnerede tom.
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-center text-[11px] text-fg3">
              <div>
                <GitBranch size={28} className="mx-auto mb-2 opacity-30" />
                <div>Vælg en fil i listen</div>
                {(!data || data.count === 0) && (
                  <div className="mt-1 text-fg3/70">
                    Når Jarvis stager edits dukker de op her.
                  </div>
                )}
              </div>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}

function FileRow({
  edit,
  active,
  onSelect,
  onDiscard,
  onApply,
  busy,
}: {
  edit: StagedEdit
  active: boolean
  onSelect: () => void
  onDiscard: () => void
  onApply: () => void
  busy: boolean
}) {
  const Icon = edit.kind === 'edit_file' ? FileEdit : FilePlus
  return (
    <div
      onClick={onSelect}
      className={[
        'group flex cursor-pointer items-center gap-2 border-b border-line/30 px-3 py-2 text-[11px] transition-colors',
        active ? 'bg-bg2 text-fg' : 'text-fg2 hover:bg-bg2/40',
      ].join(' ')}
    >
      <Icon
        size={11}
        className={[
          'flex-shrink-0',
          edit.kind === 'edit_file' ? 'text-warn' : 'text-ok',
        ].join(' ')}
      />
      <div className="min-w-0 flex-1">
        <div className="truncate font-mono" title={edit.path}>
          {shortPath(edit.path)}
        </div>
        <div className="mt-0.5 font-mono text-[9px]">
          <span className="text-ok">+{edit.additions}</span>
          <span className="mx-1 text-fg3">·</span>
          <span className="text-danger">−{edit.deletions}</span>
        </div>
      </div>
      <div className="flex flex-shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          onClick={(e) => {
            e.stopPropagation()
            onDiscard()
          }}
          disabled={busy}
          title="Discard kun denne"
          className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:bg-bg1 hover:text-danger disabled:opacity-50"
        >
          <X size={10} />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation()
            onApply()
          }}
          disabled={busy}
          title="Apply kun denne"
          className="flex h-5 w-5 items-center justify-center rounded text-fg3 hover:bg-bg1 hover:text-ok disabled:opacity-50"
        >
          <Check size={10} />
        </button>
      </div>
    </div>
  )
}

/**
 * Render a unified diff with proper add/del/hunk styling and synthetic
 * line numbers parsed from @@ headers — gives the diff a "real" feel
 * compared to raw text. Old/new line counters increment based on the
 * line type (+ advances new only, − advances old only, ctx advances both).
 */
function DiffBody({ diff }: { diff: string }) {
  const lines = diff.split('\n')
  let oldLn = 0
  let newLn = 0
  return (
    <div className="font-mono text-[12px] leading-[1.55]">
      {lines.map((line, i) => {
        let kind: 'add' | 'del' | 'hunk' | 'meta' | 'ctx' = 'ctx'
        if (line.startsWith('+++') || line.startsWith('---')) kind = 'meta'
        else if (line.startsWith('@@')) {
          kind = 'hunk'
          const m = /@@\s+-(\d+)(?:,\d+)?\s+\+(\d+)(?:,\d+)?\s+@@/.exec(line)
          if (m) {
            oldLn = parseInt(m[1], 10)
            newLn = parseInt(m[2], 10)
          }
        } else if (line.startsWith('+')) kind = 'add'
        else if (line.startsWith('-')) kind = 'del'

        const oldDisplay = kind === 'add' || kind === 'hunk' || kind === 'meta' ? '' : String(oldLn)
        const newDisplay = kind === 'del' || kind === 'hunk' || kind === 'meta' ? '' : String(newLn)
        if (kind === 'ctx') {
          oldLn++
          newLn++
        } else if (kind === 'add') {
          newLn++
        } else if (kind === 'del') {
          oldLn++
        }

        const bg =
          kind === 'add'
            ? 'rgba(63,185,80,.10)'
            : kind === 'del'
            ? 'rgba(248,81,73,.10)'
            : kind === 'hunk'
            ? 'rgba(88,166,255,.08)'
            : 'transparent'
        const fg =
          kind === 'add'
            ? '#7fdb8b'
            : kind === 'del'
            ? '#ff7b72'
            : kind === 'hunk'
            ? '#79c0ff'
            : kind === 'meta'
            ? '#6e7681'
            : '#c9d1d9'
        const sigil =
          kind === 'add' ? '+' : kind === 'del' ? '−' : kind === 'hunk' ? '@' : ' '

        return (
          <div
            key={i}
            style={{ display: 'flex', background: bg, whiteSpace: 'pre' }}
          >
            <span
              style={{
                width: '3.2em',
                padding: '0 0.3em',
                color: '#4e5262',
                flexShrink: 0,
                textAlign: 'right',
                userSelect: 'none',
                opacity: 0.7,
              }}
            >
              {oldDisplay}
            </span>
            <span
              style={{
                width: '3.2em',
                padding: '0 0.3em',
                color: '#4e5262',
                flexShrink: 0,
                textAlign: 'right',
                userSelect: 'none',
                opacity: 0.7,
                borderRight: '1px solid rgba(110,118,129,.15)',
              }}
            >
              {newDisplay}
            </span>
            <span
              style={{
                width: '1.5em',
                color: fg,
                opacity: 0.7,
                flexShrink: 0,
                textAlign: 'center',
                userSelect: 'none',
              }}
            >
              {sigil}
            </span>
            <span style={{ color: fg, flex: 1, paddingRight: '1em' }}>
              {kind === 'meta' || kind === 'hunk'
                ? line
                : line.slice(line.length > 0 ? 1 : 0)}
            </span>
          </div>
        )
      })}
    </div>
  )
}

function shortPath(path: string): string {
  const parts = path.replace(/^\/home\/[^/]+/, '~').split('/')
  if (parts.length <= 3) return parts.join('/')
  return parts.slice(0, 1).concat(['…'], parts.slice(-2)).join('/')
}
