import { useEffect, useRef, useState, type ReactNode } from 'react'
import { Check, MoreVertical } from 'lucide-react'
import { VISNINGER, VISNING_NAVN, saetStandardVisning, standardVisning, type Visning } from '../../lib/visning'

const FORKLARING: Record<Visning, string> = {
  normal: 'Runder foldet, tænkning som én linje',
  thinking: 'Et resumé af tænkningen over hver gruppe',
  verbose: 'Alt åbent — hvert kald for sig',
}

export interface MereValg {
  id: string
  navn: string
  ikon: ReactNode
  /** Sat = en kontakt (flueben når den er slået til). Udeladt = en handling. */
  aktiv?: boolean
  onClick: () => void
}

/**
 * Headerens «flere»-menu (Bjørn 19/9-2026: «rigtigt mange ikoner efter
 * central badge … smid resten i en 3-prik-menu så prikkerne står oven på
 * hinanden»).
 *
 * I headeren står kun det man bruger HELE tiden: tilbage til din besked,
 * Ændringer, Baggrundsjob (og Miljø i code). Resten bor her: Visning som
 * tre radio-valg (samme som øjet før, med «Gør til standard»), og fladens
 * kontakter — Jarvis-figuren, Filer, Preview, Panel, stemme.
 */
export function HeaderMere({ visning, onVisning, valg }: {
  visning: Visning
  onVisning: (v: Visning) => void
  valg: MereValg[]
}) {
  const [aaben, setAaben] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!aaben) return
    const luk = (e: MouseEvent) => { if (!ref.current?.contains(e.target as Node)) setAaben(false) }
    const esc = (e: KeyboardEvent) => { if (e.key === 'Escape') setAaben(false) }
    document.addEventListener('mousedown', luk)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('mousedown', luk); document.removeEventListener('keydown', esc) }
  }, [aaben])

  return (
    <div className="visning-vaelger" ref={ref}>
      <button
        type="button"
        className={`panel-toggle${aaben ? ' active' : ''}`}
        aria-label="Flere valg"
        aria-haspopup="menu"
        aria-expanded={aaben}
        title="Flere valg"
        onClick={() => setAaben((a) => !a)}
      >
        <MoreVertical size={15} strokeWidth={1.8} />
      </button>
      {aaben && (
        <div className="mode-dd-menu visning-menu header-mere-menu" role="menu" aria-label="Flere valg">
          <div className="header-mere-overskrift">Visning</div>
          {VISNINGER.map((v) => (
            <button
              key={v}
              type="button"
              role="menuitemradio"
              aria-checked={v === visning}
              className={`mode-dd-item${v === visning ? ' active' : ''}`}
              onClick={() => { if (v !== visning) onVisning(v) }}
            >
              <span className="visning-check">{v === visning ? <Check size={14} /> : null}</span>
              <span className="visning-tekst">
                <span>{VISNING_NAVN[v]}</span>
                <span className="visning-forklaring">{FORKLARING[v]}</span>
              </span>
            </button>
          ))}
          {standardVisning() !== visning && (
            <button type="button" role="menuitem" className="mode-dd-item header-mere-standard"
                    onClick={() => { saetStandardVisning(visning); setAaben(false) }}>
              <span className="visning-check" />
              <span>Gør {VISNING_NAVN[visning]} til standard</span>
            </button>
          )}
          <div className="header-mere-skille" role="separator" />
          {valg.map((o) => (
            <button
              key={o.id}
              type="button"
              role={o.aktiv === undefined ? 'menuitem' : 'menuitemcheckbox'}
              aria-checked={o.aktiv === undefined ? undefined : o.aktiv}
              className={`mode-dd-item${o.aktiv ? ' active' : ''}`}
              onClick={() => { o.onClick(); setAaben(false) }}
            >
              <span className="visning-check">{o.aktiv ? <Check size={14} /> : null}</span>
              <span className="header-mere-ikon" aria-hidden>{o.ikon}</span>
              <span>{o.navn}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
