import { useState, type ReactNode } from 'react'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'

export function WebSidebarFrame({
  web,
  sidebar,
  children,
}: {
  web: boolean
  sidebar: ReactNode
  children: ReactNode
}) {
  const [open, setOpen] = useState(false)

  if (!web) return <div className="window">{sidebar}{children}</div>

  return (
    <div className={`window web-sidebar-${open ? 'open' : 'closed'}`}>
      <div className="web-sidebar-slot">
        <button
          type="button"
          className="web-sidebar-toggle"
          aria-label={open ? 'Luk sidepanel' : 'Åbn sidepanel'}
          aria-expanded={open}
          title={open ? 'Luk sidepanel' : 'Åbn sidepanel'}
          onClick={() => setOpen((value) => !value)}
        >
          {open ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}
        </button>
        {open && <div className="web-sidebar-content">{sidebar}</div>}
      </div>
      {children}
    </div>
  )
}
