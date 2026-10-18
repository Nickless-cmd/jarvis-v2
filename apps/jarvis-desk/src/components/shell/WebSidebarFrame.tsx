import { useEffect, useRef, useState, type ReactNode } from 'react'
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
  // Bjørn 18/10-2026: «side panel skal i ui være foldet ud, men i pwa være
  // foldet ind».
  //
  // Det er BUILDET der afgør det, ikke skærmbredden. Desk-fladen (ikke-web)
  // returnerer nedenfor med panelet fast på plads — der findes ingen toggle.
  // PWA'en starter derimod ALTID foldet ind, også når browseren er 1920px bred.
  //
  // Første forsøg bandt det til `max-width: 600px` med den begrundelse at
  // fladerne deler render og derfor kun kunne skelnes på plads. Målt i browseren
  // 18/10-2026 stod panelet så ÅBENT på en bred skærm — stik imod instruksen.
  // Pladsen bestemmer stadig OM panelet ligger oven på indholdet eller står som
  // kolonne (det gør CSS'ens media query i styles/web-sidebar.css), men ikke om
  // det starter åbent.
  const [open, setOpen] = useState(false)
  const slotRef = useRef<HTMLDivElement>(null)

  // PWA: når panelet er åbent, lukker et tryk UDENFOR det — på alle bredder
  // (Bjørn 18/10-2026: «når man trykker uden for panelet når det åbent skal den
  // lukke i pwa»). Under 600px ligger det oven på indholdet; over det står det
  // som kolonne. Lukke-adfærden er den samme, for det er brugerens tryk der
  // skal lukke det, ikke et layout-tilfælde.
  useEffect(() => {
    if (!web || !open) return
    const udenfor = (event: PointerEvent) => {
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
