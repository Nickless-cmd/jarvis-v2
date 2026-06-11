import { Plus } from 'lucide-react'
import { useSessions } from '../../hooks/useSessions'
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
      <div className="sidebar-head">
        <span className="dot" /> jarvis-desk
      </div>

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
              <button
                key={s.id}
                type="button"
                className={`session-item ${s.id === activeId ? 'active' : ''}`}
                onClick={() => { select(s.id); onSurface('chat') }}
              >
                {s.title || 'Uden titel'}
              </button>
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
