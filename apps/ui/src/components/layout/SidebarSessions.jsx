import { MoreHorizontal } from 'lucide-react'
import { createPortal } from 'react-dom'
import { useEffect, useRef, useState } from 'react'

function relativeTime(dateStr) {
  if (!dateStr) return ''
  const delta = Date.now() - new Date(dateStr).getTime()
  if (isNaN(delta) || delta < 0) return ''
  const sec = Math.floor(delta / 1000)
  if (sec < 60) return 'lige nu'
  const min = Math.floor(sec / 60)
  if (min < 60) return `${min}m siden`
  const hr = Math.floor(min / 60)
  if (hr < 24) return `${hr}t siden`
  return `${Math.floor(hr / 24)}d siden`
}

function SessionMenu({ session, anchorRect, onRename, onDelete, onClose }) {
  const ref = useRef(null)

  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) onClose()
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [onClose])

  const style = {
    position: 'fixed',
    top: anchorRect.bottom + 2,
    right: window.innerWidth - anchorRect.right,
    zIndex: 9999,
  }

  return createPortal(
    <div ref={ref} className="session-dropdown" style={style}>
      <button
        className="session-dropdown-item"
        onClick={(e) => {
          e.stopPropagation()
          onClose()
          const t = window.prompt('Omdøb session', session.title)
          if (t && t !== session.title) onRename(session.id, t)
        }}
      >
        Omdøb
      </button>
      <button
        className="session-dropdown-item danger"
        onClick={(e) => {
          e.stopPropagation()
          onClose()
          if (window.confirm(`Slet "${session.title}"?`)) onDelete(session.id)
        }}
      >
        Slet
      </button>
    </div>,
    document.body
  )
}

export function SidebarSessions({ sessions, activeSessionId, onSelect, onRename, onDelete }) {
  const [menuState, setMenuState] = useState(null) // { id, rect }

  function openMenu(e, session) {
    e.stopPropagation()
    const rect = e.currentTarget.getBoundingClientRect()
    setMenuState(menuState?.id === session.id ? null : { id: session.id, rect, session })
  }

  return (
    <section className="sidebar-sessions">
      <div className="sidebar-sessions-head">
        <span className="sidebar-mini-label mono">Seneste</span>
      </div>

      <div className="session-list">
        {sessions.map((session) => (
          <div
            className={session.id === activeSessionId ? 'session-item active' : 'session-item'}
            key={session.id}
            onClick={() => onSelect(session.id)}
            title={session.title}
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onSelect(session.id)}
            role="button"
          >
            <div className="session-item-body">
              <div className="session-item-title">{session.title}</div>
              <div className="session-item-time mono">{relativeTime(session.updated_at)}</div>
            </div>
            <button
              className="session-menu-btn"
              onClick={(e) => openMenu(e, session)}
              title="Mere"
            >
              <MoreHorizontal size={12} />
            </button>
          </div>
        ))}

        {!sessions.length ? (
          <div className="sidebar-empty-state">
            <span>Ingen chats endnu</span>
          </div>
        ) : null}
      </div>

      {menuState && (
        <SessionMenu
          session={menuState.session}
          anchorRect={menuState.rect}
          onRename={onRename}
          onDelete={onDelete}
          onClose={() => setMenuState(null)}
        />
      )}
    </section>
  )
}
