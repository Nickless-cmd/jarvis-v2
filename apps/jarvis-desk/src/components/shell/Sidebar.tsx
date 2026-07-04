import { useEffect, useRef, useState, Fragment } from 'react'
import {
  Plus, MoreHorizontal, Pencil, Download, Trash2, Search, X, Images, Code,
  LayoutDashboard, Blocks, Settings, Brain, Cpu,
  User, ShieldCheck, Bell, Palette, Languages, MapPin, Database, Folder, Plug, Bot, Info,
  type LucideIcon,
} from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
import { TeamsSection } from './TeamsSection'
import { useSettings } from '../../hooks/useSettings'
import { useStream } from '../../hooks/useStream'
import { searchSessions, getActiveRuns, type SessionSearchResult } from '../../lib/api'
import { COWORK_ZONES, emitZone, onZone, normalizeZone, type Zone } from '../../lib/coworkZone'
import { ModeSlider, type Mode } from './ModeSlider'
import { SecondaryNav, type SecondarySurface } from './SecondaryNav'
import { SystemHealth } from './SystemHealth'

const ZONE_ICONS: Record<string, LucideIcon> = {
  LayoutDashboard, Blocks, Settings, Brain, Cpu,
  User, ShieldCheck, Bell, Palette, Languages, MapPin, Database, Folder, Plug, Bot, Info,
}

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
  const { sessions, activeId, select, newChat } = useSessions()
  const { settings } = useSettings()
  const { workingSessionId, canonicalErrors } = useStream()

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

      {surface === 'cowork' ? (
        <CoworkMenu />
      ) : (
      <div className="sessions">
        <button className="new-chat" type="button" onClick={() => newChat()}>
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
                  workspaceKind={s.workspace_kind}
                  onSelect={() => { select(s.id); onSurface(s.workspace_kind ? 'code' : 'chat') }}
                />
              ))}
            </>
          )
        )}
      </div>
      )}

      {(surface === 'chat' || surface === 'code') && (
        <TeamsSection onOpenSession={(id) => { select(id); onSurface('chat') }} />
      )}

      <div className="sidebar-foot">
        <div className="who">
          <span className="avatar">{userName.charAt(0).toUpperCase()}</span>
          <span>{userName}</span>
        </div>
        <SystemHealth errors={canonicalErrors} />
        <SecondaryNav active={surface} onSelect={(s) => onSurface(s)} />
      </div>
    </aside>
  )
}

/** Cowork-menu i venstre panel (mode-bevidst): en FLAD liste af klare destinationer —
 *  hver indstillings-sektion sit eget punkt, grupperet med scanbare overskrifter (Bjørn
 *  2026-07-01: simpelhed slår kompakthed; Mikkel skal bæres igennem). Zone-skift via emitZone. */
function CoworkMenu() {
  const [zone, setZone] = useState<Zone>('mc')
  const { auth } = useSettings()
  const isOwner = auth?.role === 'owner'
  // Hold lokal markering i sync med Jarvis-styret zone-skift (open_ui_panel); 'settings' → 'konto'.
  useEffect(() => onZone((z) => setZone(normalizeZone(z))), [])
  const visible = COWORK_ZONES.filter((z) => isOwner || !z.ownerOnly)
  let lastGroup = ''
  return (
    <div className="sessions cowork-menu">
      {visible.map((z) => {
        const Icon = ZONE_ICONS[z.icon] ?? Blocks
        const header = z.group !== lastGroup ? z.group : null
        lastGroup = z.group
        return (
          <Fragment key={z.id}>
            {header && <div className="sidebar-label">{header}</div>}
            <button
              type="button"
              className={`sidebar-nav-row ${zone === z.id ? 'active' : ''}`}
              onClick={() => { setZone(z.id); emitZone(z.id) }}
            >
              <Icon size={14} /> {z.label}
            </button>
          </Fragment>
        )
      })}
    </div>
  )
}

/** Session-række med "..."-menu (omdøb / eksportér / slet) — vises ved hover. */
function SessionItem({
  id,
  title,
  active,
  working,
  workspaceKind,
  onSelect,
}: {
  id: string
  title: string
  active: boolean
  working?: boolean
  workspaceKind?: string | null
  onSelect: () => void
}) {
  const { rename, remove } = useSessions()
  const { settings } = useSettings()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState(title)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (!open) return
    const close = () => { setOpen(false); setConfirmDelete(false) }
    window.addEventListener('click', close)
    return () => window.removeEventListener('click', close)
  }, [open])

  useEffect(() => {
    if (editing) { setDraft(title); inputRef.current?.focus(); inputRef.current?.select() }
  }, [editing, title])

  // Omdøb via INLINE edit — window.prompt() er ikke understøttet i Electron.
  const commitRename = () => {
    const next = draft.trim()
    if (next && next !== title) void rename(id, next)
    setEditing(false)
  }
  const doExport = async () => {
    setOpen(false)
    if (!settings) return
    const { exportSessionMarkdown } = await import('../../lib/exportSession')
    await exportSessionMarkdown({ apiBaseUrl: settings.apiBaseUrl, authToken: settings.authToken }, id, title)
  }
  // Slet via to-trins INLINE bekræft — window.confirm() er upålidelig i Electron.
  const doDelete = () => {
    if (!confirmDelete) { setConfirmDelete(true); return }
    setOpen(false)
    setConfirmDelete(false)
    void remove(id)
  }

  return (
    <div className={`session-item ${active ? 'active' : ''} ${working ? 'working' : ''}`}>
      {editing ? (
        <input
          ref={inputRef}
          className="session-rename-input"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { e.preventDefault(); commitRename() }
            else if (e.key === 'Escape') { e.preventDefault(); setEditing(false) }
          }}
          onBlur={commitRename}
        />
      ) : (
        <button type="button" className="session-item-label" onClick={onSelect}>
          {working && (
            <span className="session-working" aria-label="Jarvis arbejder" title="Jarvis arbejder her">
              <span></span><span></span><span></span>
            </span>
          )}
          {workspaceKind && <Code size={12} className="session-mode-icon" />}
          {title}
        </button>
      )}
      <div className="session-menu-anchor" onClick={(e) => e.stopPropagation()}>
        <button type="button" className="session-more" aria-label="Mere" onClick={() => { setOpen((o) => !o); setConfirmDelete(false) }}>
          <MoreHorizontal size={15} />
        </button>
        {open && (
          <div className="session-menu">
            <button type="button" onClick={() => { setOpen(false); setEditing(true) }}><Pencil size={13} /> Omdøb</button>
            <button type="button" onClick={doExport}><Download size={13} /> Eksportér</button>
            <button type="button" className="danger" onClick={doDelete}>
              <Trash2 size={13} /> {confirmDelete ? 'Slet for altid?' : 'Slet'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
