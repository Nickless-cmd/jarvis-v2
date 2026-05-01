import { useEffect, useRef, useState } from 'react'
import { createPortal } from 'react-dom'
import { Search, X, MessageSquare } from 'lucide-react'

interface SearchHit {
  message_id: string
  session_id: string
  session_title: string
  role: string
  snippet: string
  created_at: string
  user_id: string
  workspace_name: string
}

interface SearchResp {
  q: string
  scope: string
  count: number
  hits: SearchHit[]
}

interface Props {
  apiBaseUrl: string
  onClose: () => void
  onPick: (hit: SearchHit) => void
}

/**
 * Cmd/Ctrl+K modal for searching chat content across all sessions in
 * the current workspace. Live-debounced — re-fetches 200ms after the
 * user stops typing. Result list is keyboard-navigable.
 *
 * Why scope=current_workspace: prevents Bjørn from accidentally seeing
 * Mikkel's chat hits when he searches. Workspace is bound by the
 * X-JarvisX-User middleware before this endpoint runs.
 */
export function CrossSessionSearchModal({ apiBaseUrl, onClose, onPick }: Props) {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SearchHit[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [highlight, setHighlight] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)
  const debounceRef = useRef<number | null>(null)

  useEffect(() => {
    inputRef.current?.focus()
  }, [])

  useEffect(() => {
    if (!q.trim() || q.trim().length < 2) {
      setHits([])
      return
    }
    if (debounceRef.current) window.clearTimeout(debounceRef.current)
    debounceRef.current = window.setTimeout(async () => {
      setLoading(true)
      setError(null)
      try {
        const url = `${apiBaseUrl.replace(/\/$/, '')}/api/chat/search?q=${encodeURIComponent(
          q,
        )}&scope=current_workspace&limit=80`
        const res = await fetch(url)
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        const j = (await res.json()) as SearchResp
        setHits(j.hits || [])
        setHighlight(0)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e))
      } finally {
        setLoading(false)
      }
    }, 200)
    return () => {
      if (debounceRef.current) window.clearTimeout(debounceRef.current)
    }
  }, [q, apiBaseUrl])

  const handleKey = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      e.preventDefault()
      onClose()
      return
    }
    if (hits.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlight((i) => (i + 1) % hits.length)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlight((i) => (i - 1 + hits.length) % hits.length)
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (hits[highlight]) onPick(hits[highlight])
    }
  }

  return createPortal(
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,.65)',
        zIndex: 10000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '12vh',
      }}
      onClick={onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[70vh] w-[680px] max-w-[95vw] flex-col rounded-lg border border-line2 bg-bg1 shadow-2xl"
      >
        <div className="flex flex-shrink-0 items-center gap-2 border-b border-line px-4 py-3">
          <Search size={14} className="text-accent" />
          <input
            ref={inputRef}
            type="text"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={handleKey}
            placeholder="Search across all your chats…"
            className="flex-1 bg-transparent text-sm text-fg placeholder:text-fg3 focus:outline-none"
          />
          {loading && (
            <span className="font-mono text-[10px] text-fg3">searching…</span>
          )}
          <button
            onClick={onClose}
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            <X size={12} />
          </button>
        </div>

        <div className="min-h-[80px] flex-1 overflow-y-auto">
          {error && (
            <div className="px-4 py-3 font-mono text-[11px] text-danger">{error}</div>
          )}
          {!error && q.trim().length >= 2 && hits.length === 0 && !loading && (
            <div className="px-4 py-6 text-center text-xs text-fg3">No matches.</div>
          )}
          {q.trim().length < 2 && (
            <div className="px-4 py-6 text-center text-[11px] text-fg3">
              Type at least 2 characters to search.
            </div>
          )}
          {hits.map((h, i) => {
            const isActive = i === highlight
            return (
              <button
                key={h.message_id}
                onMouseEnter={() => setHighlight(i)}
                onClick={() => onPick(h)}
                className={[
                  'flex w-full flex-col items-start gap-1 border-b border-line/40 px-4 py-2 text-left transition-colors',
                  isActive ? 'bg-accent/10' : 'hover:bg-bg2/50',
                ].join(' ')}
              >
                <div className="flex w-full items-center gap-2">
                  <MessageSquare
                    size={10}
                    className={isActive ? 'text-accent' : 'text-fg3'}
                  />
                  <span
                    className={`flex-1 truncate text-xs font-medium ${
                      isActive ? 'text-accent' : 'text-fg2'
                    }`}
                  >
                    {h.session_title || h.session_id.slice(0, 16) + '…'}
                  </span>
                  <span className="font-mono text-[9px] text-fg3">
                    {h.role} · {formatTime(h.created_at)}
                  </span>
                </div>
                <div className="line-clamp-2 text-[11px] text-fg3">{h.snippet}</div>
              </button>
            )
          })}
        </div>

        <div className="flex flex-shrink-0 items-center justify-between border-t border-line/60 bg-bg1/40 px-4 py-1.5 text-[10px] text-fg3">
          <span>
            ↑↓ navigate · Enter open · Esc close
          </span>
          <span>{hits.length > 0 ? `${hits.length} hits` : ''}</span>
        </div>
      </div>
    </div>,
    document.body,
  )
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    if (isNaN(d.getTime())) return iso
    const delta = Date.now() - d.getTime()
    const sec = Math.floor(delta / 1000)
    if (sec < 60) return 'now'
    const min = Math.floor(sec / 60)
    if (min < 60) return `${min}m`
    const hr = Math.floor(min / 60)
    if (hr < 24) return `${hr}h`
    const day = Math.floor(hr / 24)
    if (day < 30) return `${day}d`
    return d.toISOString().slice(0, 10)
  } catch {
    return iso
  }
}
