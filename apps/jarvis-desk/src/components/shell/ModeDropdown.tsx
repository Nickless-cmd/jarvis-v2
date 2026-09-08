import { useEffect, useRef, useState } from 'react'
import { ChevronDown, MessageSquare, LayoutGrid, Code2 } from 'lucide-react'

const MODES = ['chat', 'cowork', 'code'] as const
export type Mode = (typeof MODES)[number]

const NAVN: Record<Mode, string> = { chat: 'Chat', cowork: 'Arbejde', code: 'Code' }
const IKON = { chat: MessageSquare, cowork: LayoutGrid, code: Code2 } as const

/**
 * Mode-vælger som dropdown (Bjørn 8/9-2026 — afløser pille-slideren).
 *
 * Slideren viste alle tre valg hele tiden og brugte hele panelets bredde på at
 * fortælle noget man allerede vidste: hvor man var. En dropdown viser den
 * aktive tilstand og gemmer de to andre bag ét klik — og frigør pladsen ved
 * siden af til noget der faktisk skal bruges.
 */
export function ModeDropdown({ active, onChange }: { active: Mode; onChange: (m: Mode) => void }) {
  const [open, setOpen] = useState(false)
  const rod = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    // Klik udenfor OG Escape lukker. Uden Escape ville en åben menu kunne
    // fange tastaturet for en der ikke bruger mus.
    const luk = (e: MouseEvent) => { if (!rod.current?.contains(e.target as Node)) setOpen(false) }
    const tast = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('mousedown', luk)
    window.addEventListener('keydown', tast)
    return () => { window.removeEventListener('mousedown', luk); window.removeEventListener('keydown', tast) }
  }, [open])

  const Aktiv = IKON[active]
  return (
    <div className="mode-dd" ref={rod}>
      <button
        type="button"
        className="mode-dd-btn"
        aria-haspopup="listbox"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <Aktiv size={14} />
        <span className="mode-dd-navn">{NAVN[active]}</span>
        <ChevronDown size={13} className="mode-dd-chevron" />
      </button>
      {open && (
        <div className="mode-dd-menu" role="listbox">
          {MODES.map((m) => {
            const Ikon = IKON[m]
            return (
              <button
                key={m}
                type="button"
                role="option"
                aria-selected={m === active}
                className={`mode-dd-item ${m === active ? 'active' : ''}`}
                onClick={() => { onChange(m); setOpen(false) }}
              >
                <Ikon size={14} /> {NAVN[m]}
              </button>
            )
          })}
        </div>
      )}
    </div>
  )
}
