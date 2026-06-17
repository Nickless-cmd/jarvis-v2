import { useEffect, useRef, useState } from 'react'
import type { ApiConfig } from '../lib/api'
import { searchSessions, type SessionHit } from '../lib/sessionSearchApi'

/** Ctrl/Cmd+K søge-palette på tværs af sessioner (§14.3). Debounced, tastatur-venlig.
 *  Prop-drevet → testbar. onSelect(session_id) skifter session; Esc/baggrund lukker. */
export function SessionSearch({
  open,
  config,
  onSelect,
  onClose,
}: {
  open: boolean
  config?: ApiConfig
  onSelect: (sessionId: string) => void
  onClose: () => void
}) {
  const [q, setQ] = useState('')
  const [hits, setHits] = useState<SessionHit[]>([])
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return undefined
    setQ('')
    setHits([])
    const id = setTimeout(() => inputRef.current?.focus(), 0)
    return () => clearTimeout(id)
  }, [open])

  useEffect(() => {
    if (!open || !config || !q.trim()) {
      setHits([])
      return
    }
    let cancelled = false
    const t = setTimeout(() => {
      searchSessions(config, q).then((r) => { if (!cancelled) setHits(r) }).catch(() => {})
    }, 200)
    return () => { cancelled = true; clearTimeout(t) }
  }, [q, open, config])

  if (!open) return null

  const pick = (id: string) => { onSelect(id); onClose() }

  return (
    <div className="search-overlay" onClick={onClose}>
      <div className="search-box" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="search-input"
          type="text"
          placeholder="Søg i samtaler…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') onClose()
            if (e.key === 'Enter' && hits[0]) pick(hits[0].session_id)
          }}
        />
        <div className="search-results">
          {q.trim() && hits.length === 0 && <div className="search-empty">Ingen match.</div>}
          {hits.map((h) => (
            <button key={h.session_id} type="button" className="search-hit" onClick={() => pick(h.session_id)}>
              <span className="search-hit-title">{h.title || '(uden titel)'}</span>
              {h.snippet && <span className="search-hit-snippet">{h.snippet}</span>}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
