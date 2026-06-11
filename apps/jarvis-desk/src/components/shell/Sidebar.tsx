import { useEffect, useState } from 'react'
import { Plus, MoreHorizontal, Pencil, Download, Trash2 } from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
import { useSettings } from '../../hooks/useSettings'
import { ModeSlider, type Mode } from './ModeSlider'
import { SecondaryNav, type SecondarySurface } from './SecondaryNav'

export type Surface = Mode | SecondarySurface

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
        {sessions.length > 0 && (
          <>
            <div className="sidebar-label">samtaler</div>
            {sessions.map((s) => (
              <SessionItem
                key={s.id}
                id={s.id}
                title={s.title || 'Uden titel'}
                active={s.id === activeId}
                onSelect={() => { select(s.id); onSurface('chat') }}
              />
            ))}
          </>
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
  onSelect,
}: {
  id: string
  title: string
  active: boolean
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
    <div className={`session-item ${active ? 'active' : ''}`}>
      <button type="button" className="session-item-label" onClick={onSelect}>{title}</button>
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
