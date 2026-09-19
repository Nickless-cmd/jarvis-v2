import { useEffect, useRef, useState } from 'react'
import { Check, Eye } from 'lucide-react'
import { VISNINGER, VISNING_NAVN, saetStandardVisning, standardVisning, type Visning } from '../../lib/visning'

const FORKLARING: Record<Visning, string> = {
  normal: 'Runder foldet, tænkning som én linje',
  thinking: 'Et resumé af tænkningen over hver gruppe',
  verbose: 'Alt åbent — hvert kald for sig',
}

/**
 * Vælgeren for samtalens visning — Claude Desktops «Transcript view»-menu
 * (cc-desktop-chatview.md §1): tre radio-punkter, et skift gælder KUN denne
 * samtale, og «Gør til standard» sætter det nye samtaler åbner i.
 *
 * Et skift står kort som besked på knappen («Visning: Tænkning») — deres
 * toast «Switched transcript view to Thinking».
 */
export function VisningVaelger({ visning, onSkift }: { visning: Visning; onSkift: (v: Visning) => void }) {
  const [aaben, setAaben] = useState(false)
  const [besked, setBesked] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!aaben) return
    const luk = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setAaben(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setAaben(false) }
    document.addEventListener('mousedown', luk)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', luk); document.removeEventListener('keydown', esc) }
  }, [aaben])

  useEffect(() => {
    if (!besked) return
    const t = setTimeout(() => setBesked(null), 2400)
    return () => clearTimeout(t)
  }, [besked])

  const vaelg = (v: Visning) => {
    setAaben(false)
    if (v === visning) return
    onSkift(v)
    setBesked(`Visning: ${VISNING_NAVN[v]}`)
  }

  return (
    <div className="visning-vaelger" ref={ref}>
      <button
        type="button"
        className={`panel-toggle${visning !== 'normal' ? ' active' : ''}`}
        aria-label={`Visning: ${VISNING_NAVN[visning]}`}
        aria-haspopup="menu"
        aria-expanded={aaben}
        title={`Visning: ${VISNING_NAVN[visning]}`}
        onClick={() => setAaben((a) => !a)}
      >
        <Eye size={15} />
      </button>
      {besked ? <span className="visning-besked" role="status">{besked}</span> : null}
      {aaben && (
        <div className="mode-dd-menu visning-menu" role="menu" aria-label="Visning">
          {VISNINGER.map((v) => (
            <button
              key={v}
              type="button"
              role="menuitemradio"
              aria-checked={v === visning}
              className={`mode-dd-item${v === visning ? ' active' : ''}`}
              onClick={() => vaelg(v)}
            >
              <span className="visning-check">{v === visning ? <Check size={14} /> : null}</span>
              <span className="visning-tekst">
                <span>{VISNING_NAVN[v]}</span>
                <span className="visning-forklaring">{FORKLARING[v]}</span>
              </span>
            </button>
          ))}
          {standardVisning() !== visning && (
            <button type="button" role="menuitem" className="mode-dd-item visning-standard" onClick={() => { saetStandardVisning(visning); setAaben(false); setBesked(`${VISNING_NAVN[visning]} er nu standard`) }}>
              Gør {VISNING_NAVN[visning]} til standard
            </button>
          )}
        </div>
      )}
    </div>
  )
}
