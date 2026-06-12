import { useEffect, useState } from 'react'
import { Plus, MoreHorizontal, Pencil, Download, Trash2, Search, X, Images } from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import { useStream } from '../../hooks/useStream'
import { searchSessions, getActiveRuns, type SessionSearchResult } from '../../lib/api'
import { ModeSlider, type Mode } from './ModeSlider'
import { SecondaryNav, type SecondarySurface } from './SecondaryNav'

export type Surface = Mode | SecondarySurface | 'gallery'

/** Sidebar: app-navn, mode-slider, session-liste, sekundær-nav + bruger-fod. */
export function Sidebar({
  surface,
  onSurface,
  userName,
}: {
  surface: Surface
  onSurface: (s: Surface) => void
  userName: string
}) {
  const { sessions, activeId, select, create } = useSessions()
  const { settings } = useSettings()
  const { workingSessionId } = useStream()

  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SessionSearchResult[]>([])
  const searching = query.trim().length > 0

  // #8: poll backend for sessioner med aktivt run (også autonome baggrunds-runs
  // som klienten ikke selv driver). Union'es med workingSessionId fra streamen.
  const [activeRunSessions, setActiveRunSessions] = useState<Set<string>>(new Set())
  useEffect(() => {
    if (!settings) return
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    const tick = () => {
      void getActiveRuns(cfg)
        .then((ids) => { if (!cancelled) setActiveRunSessions(new Set(ids)) })
        .catch(() => { /* behold sidste — ingen flicker ved netværks-blip */ })
    }
    tick()
    const id = setInterval(tick, 4000)
    return () => { cancelled = true; clearInterval(id) }
  }, [settings])
  const isWorking = (id: string) => id === workingSessionId || activeRunSessions.has(id)

  // Debounced søgning mod backend (titel + besked-indhold).
  useEffect(() => {
    const q = query.trim()
    if (!q || !settings) { setResults([]); return }
    const cfg = { apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }
    let cancelled = false
    const t = setTimeout(() => {
      void searchSessions(cfg, q)
        .then((r) => { if (!cancelled) setResults(r) })
        .catch(() => { if (!cancelled) setResults([]) })
    }, 220)
    return () => { cancelled = true; clearTimeout(t) }
  }, [query, settings])

  return (
    <aside className="sidebar">
      <ModeSlider
        active={(['chat', 'cowork', 'code'] as const).includes(surface as Mode) ? (surface as Mode) : 'chat'}
        onChange={(m) => onSurface(m)}
      />

      <div className="sessions">
        <button className="new-chat" type="button" onClick={() => void create('Ny samtale')}>
          <Plus size={14} /> Ny samtale
        </button>

        <button
          type="button"
          className={`sidebar-nav-row ${surface === 'gallery' ? 'active' : ''}`}
          onClick={() => onSurface('gallery')}
        >
          <Images size={14} /> Billeder
        </button>

        <div className="session-search">
          <Search size={13} className="session-search-icon" />
          <input
            type="text"
            placeholder="Søg i samtaler…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
          {query && (
            <button type="button" className="session-search-clear" aria-label="Ryd søgning" onClick={() => setQuery('')}>
              <X size={13} />
            </button>
          )}
        </div>

        {searching ? (
          <>
            <div className="sidebar-label">resultater</div>
            {results.length === 0 ? (
              <div className="session-search-empty">Ingen samtaler matcher</div>
            ) : (
              results.map((r) => (
                <button
                  key={r.session_id}
                  type="button"
                  className={`session-result ${r.session_id === activeId ? 'active' : ''}`}
                  onClick={() => { select(r.session_id); onSurface('chat'); setQuery('') }}
                >
                  <span className="session-result-title">{r.title}</span>
                  {r.snippet && <span className="session-result-snippet">{r.snippet}</span>}
                </button>
              ))
            )}
          </>
        ) : (
          sessions.length > 0 && (
            <>
              <div className="sidebar-label">samtaler</div>
              {sessions.map((s) => (
                <SessionItem
                  key={s.id}
                  id={s.id}
                  title={s.title || 'Uden titel'}
                  active={s.id === activeId}
                  working={isWorking(s.id)}
                  onSelect={() => { select(s.id); onSurface('chat') }}
                />
              ))}
            </>
          )
        )}
      </div>

      <div className="sidebar-foot">
        <div className="who">
          <span className="avatar">{userName.charAt(0).toUpperCase()}</span>
          <span>{userName}</span>
        </div>
        <SecondaryNav active={surface} onSelect={(s) => onSurface(s)} />
      </div>
    </aside>
  )
}

/** Session-række med "..."-menu (omdøb / eksportér / slet) — vises ved hover. */
function SessionItem({
  id,
  title,
  active,
  working,
  onSelect,
}: {
  id: string
  title: string
  active: boolean
  working?: boolean
  onSelect: () => void
}) {
  const { rename, remove } = useSessions()
  const { settings } = useSettings()
  const [open, setOpen] = useState(false)

  useEffect(() => {
    if (!open) return
    const close = () => setOpen(false)
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [open])

  const doRename = () => {
    const next = window.prompt('Omdøb samtale', title)
    if (next && next.trim() && next.trim() !== title) void rename(id, next.trim())
    setOpen(false)
  }
  const doExport = async () => {
    setOpen(false)
    if (!settings) return
    const { exportSessionMarkdown } = await import('../../lib/exportSession')
    await exportSessionMarkdown({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }, id, title)
  }
  const doDelete = () => {
    setOpen(false)
    if (window.confirm(`Slet samtalen "${title}"?`)) void remove(id)
  }

  return (
    <div className={`session-item ${active ? 'active' : ''} ${working ? 'working' : ''}`}>
      <button type="button" className="session-item-label" onClick={onSelect}>
        {working && (
          <span className="session-working" aria-label="Jarvis arbejder" title="Jarvis arbejder her">
            <span></span><span></span><span></span>
          </span>
        )}
        {title}
      </button>
      <div className="session-menu-anchor" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="session-more" aria-label="Mere" onClick={() => setOpen((o) => !o)}>
          <MoreHorizontal size={15} />
        </button>
        {open && (
          <div className="session-menu">
            <button type="button" onClick={doRename}><Pencil size={13} /> Omdøb</button>
            <button type="button" onClick={doExport}><Download size={13} /> Eksportér</button>
            <button type="button" className="danger" onClick={doDelete}><Trash2 size={13} /> Slet</button>
          </div>
        )}
      </div>
    </div>
  )
}
