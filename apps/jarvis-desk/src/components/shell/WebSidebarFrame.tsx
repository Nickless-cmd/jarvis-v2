import { useEffect, useRef, useState, type ReactNode } from 'react'
import { PanelLeftClose, PanelLeftOpen } from 'lucide-react'

/**
 * Samme brækpunkt som CSS'ens overlay-layout (styles/web-sidebar.css).
 * Under det ligger panelet OVEN PÅ indholdet; over det står det som en kolonne
 * ved siden af. Grænsen skal læses ét sted — derfor denne konstant og den
 * matchende media query, ikke to forskellige tal.
 */
const SMAL = '(max-width: 600px)'

function erSmal() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia(SMAL).matches
}

export function WebSidebarFrame({
  web,
  sidebar,
  children,
}: {
  web: boolean
  sidebar: ReactNode
  children: ReactNode
}) {
  // Bjørn 18/10-2026: «side panel skal i ui være foldet ud, men i pwa være
  // foldet ind». Desk, ui og pwa deler render — så forskellen kan ikke være
  // hvilken app der kører, men hvor meget plads der er. En bred flade har råd
  // til kolonnen; en telefon har ikke, og der skal panelet starte inde.
  const [open, setOpen] = useState(() => !erSmal())
  const slotRef = useRef<HTMLDivElement>(null)

  // PWA: når panelet ligger oven på indholdet, skal et tryk UDENFOR lukke det
  // (Bjørn 18/10-2026). I kolonne-layoutet rammer et klik ved siden af aldrig
  // panelet — der er det synligt hele tiden, og skal ikke lukke af et tilfælde.
  useEffect(() => {
    if (!web || !open) return
    const udenfor = (event: PointerEvent) => {
      if (!erSmal()) return
      const slot = slotRef.current
      if (!slot || slot.contains(event.target as Node)) return
      setOpen(false)
    }
    document.addEventListener('pointerdown', udenfor)
    return () => document.removeEventListener('pointerdown', udenfor)
  }, [web, open])

  if (!web) return <div className="window">{sidebar}{children}</div>

  return (
    <div className={`window web-sidebar-${open ? 'open' : 'closed'}`}>
      <div className="web-sidebar-slot" ref={slotRef}>
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
