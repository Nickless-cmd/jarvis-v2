import { useEffect, useRef, useState } from 'react'
import { filtrerHandlinger } from '../lib/paletteActions'
import type { ApiConfig } from '../lib/api'
import { searchSessions, type SessionHit } from '../lib/sessionSearchApi'

/** Ctrl/Cmd+K søge-palette på tværs af sessioner (§14.3). Debounced, tastatur-venlig.
 *  Prop-drevet → testbar. onSelect(session_id) skifter session; Esc/baggrund lukker. */
export function SessionSearch({
  open,
  config,
  onSelect,
  onClose,
  onNavigate,
  erEjer = false,
}: {
  open: boolean
  config?: ApiConfig
  onSelect: (sessionId: string) => void
  onClose: () => void
  /** Naviger til en flade/zone. Uden den vises kun samtaler (bagudkompat). */
  onNavigate?: (id: string) => void
  erEjer?: boolean
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
  const gaaTil = (id: string) => { onNavigate?.(id); onClose() }
  const handlinger = onNavigate ? filtrerHandlinger(q, erEjer).slice(0, 6) : []

  return (
    <div className="search-overlay" onClick={onClose}>
      <div className="search-box" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          className="search-input"
          type="text"
          placeholder={onNavigate ? 'Søg i samtaler, eller gå til…' : 'Søg i samtaler…'}
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') onClose()
            if (e.key === 'Enter') {
              // Handlinger vinder ved tom soegning: skriver man «arbejde» og
              // trykker retur, vil man DERHEN — ikke ind i en samtale der
              // tilfaeldigvis naevner ordet.
              if (handlinger[0] && !hits[0]) { gaaTil(handlinger[0].id); return }
              if (hits[0]) pick(hits[0].session_id)
            }
          }}
        />
        <div className="search-results">
          {handlinger.length > 0 && (
            <>
              <div className="search-gruppe">Gå til</div>
              {handlinger.map((h) => (
                <button key={h.id} type="button" className="search-hit"
                        onClick={() => gaaTil(h.id)}>
                  <span className="search-hit-title">{h.navn}</span>
                  {h.hvad && <span className="search-hit-snippet">{h.hvad}</span>}
                </button>
              ))}
              {hits.length > 0 && <div className="search-gruppe">Samtaler</div>}
            </>
          )}
          {q.trim() && hits.length === 0 && handlinger.length === 0 && (
            <div className="search-empty">Ingen match.</div>
          )}
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
