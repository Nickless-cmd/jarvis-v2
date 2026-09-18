/**
 * Den delte inspektør — detaljen om ÉN ting, til højre for tabellen.
 *
 * Én inspektør for alle faner, ikke en pr. tabel: to paneler der kan stå åbne
 * samtidig ville lade brugeren se to forskellige ting og tro det var den samme.
 *
 * ## Hvorfor fokus føres tilbage
 *
 * Inspektøren åbnes fra en række. Lukkes den uden at fokus vender tilbage,
 * lander tastaturet i toppen af dokumentet, og man skal tabbe sig gennem hele
 * tabellen igen for at komme hen til den række man lige stod på. Det gør
 * fladen ubrugelig uden mus — og det er billigt at undgå.
 */
import { useEffect, useRef } from 'react'
import { X } from 'lucide-react'

export interface InspektorFelt {
  navn: string
  vaerdi: string
  /** Sat → vises som et mærkat frem for tekst (fx en kilde eller en status). */
  maerkat?: boolean
}

export function CheapLaneInspector({
  titel, undertitel, felter, children, onLuk, tilbageTil,
}: {
  titel: string
  undertitel?: string
  felter?: InspektorFelt[]
  children?: React.ReactNode
  onLuk: () => void
  /** Elementet der åbnede inspektøren — fokus vender hertil ved lukning. */
  tilbageTil?: HTMLElement | null
}) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    ref.current?.focus()
    const påTast = (e: KeyboardEvent) => { if (e.key === 'Escape') onLuk() }
    window.addEventListener('keydown', påTast)
    return () => {
      window.removeEventListener('keydown', påTast)
      // Tilbage til rækken — ikke til toppen af dokumentet.
      try { tilbageTil?.focus() } catch { /* elementet kan være væk */ }
    }
  }, [onLuk, tilbageTil])

  return (
    <aside className="cl-inspektor" aria-label={titel} tabIndex={-1} ref={ref}>
      <div className="cl-inspektor-hoved">
        <div>
          <h4>{titel}</h4>
          {undertitel ? <p className="cl-dæmpet">{undertitel}</p> : null}
        </div>
        <button type="button" onClick={onLuk} aria-label="Luk">
          <X size={15} aria-hidden="true" />
        </button>
      </div>

      {felter?.length ? (
        <dl className="cl-inspektor-felter">
          {felter.map((f) => (
            <div key={f.navn}>
              <dt>{f.navn}</dt>
              <dd>{f.maerkat ? <span className="cl-kilde">{f.vaerdi}</span> : f.vaerdi}</dd>
            </div>
          ))}
        </dl>
      ) : null}

      {children}
    </aside>
  )
}
