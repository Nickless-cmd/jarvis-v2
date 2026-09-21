import type { ReactNode } from 'react'
import { AlertTriangle, Inbox, Loader2 } from 'lucide-react'

/**
 * Listens tre tilstande — ÉN gang, så de ser ens ud overalt.
 *
 * ## Hvorfor (Codex' punkt 2, videregivet af Bjørn 21/9-2026)
 *
 * «Jeg fandt konkrete steder, hvor fejl bliver til tomme lister eller
 * manglende status. Brugeren skal kunne se forskel på: der er endnu ikke
 * tilføjet noget / det bliver hentet / det kunne ikke hentes — prøv igen.»
 *
 * Målt i 0.6.64: 18 komponenter henter data ind i en liste, og **14 af dem
 * havde ingen fejl-tilstand overhovedet**. Falder kaldet, står der det samme
 * som når kassen bare er tom — og så leder man efter noget man selv har
 * gjort forkert. (Én af de fjorten var min egen browser-rude fra samme aften.)
 *
 * Rettelsen er ikke fjorten lapper. Den er ét sted der kan sige forskellen,
 * så den femtende komponent arver den uden at nogen skal huske det.
 *
 * `onIgen` er med vilje IKKE valgfri når der er en fejl: en fejlbesked uden
 * en vej videre er en blindgyde. Er handlingen umulig, siger kalderen det
 * eksplicit med `onIgen={null}`.
 */
export interface ListeTilstandProps {
  /** Henter vi lige nu? Vinder over alt andet. */
  henter?: boolean
  /** Fejlen, hvis hentningen slog fejl. Tom streng = ingen fejl. */
  fejl?: string
  /** Hvor mange elementer listen fik. 0 + ingen fejl = ægte tom. */
  antal: number
  /** Hvad der står når kassen er tom, fordi der ikke ER noget endnu. */
  tomTekst: string
  /** Prøv igen. `null` når der ikke findes en vej videre. */
  onIgen: (() => void) | null
  /** Selve listen. Vises kun når der er noget at vise. */
  children?: ReactNode
}

export function ListeTilstand({
  henter = false, fejl = '', antal, tomTekst, onIgen, children,
}: ListeTilstandProps) {
  // Rækkefølgen er en påstand: HENTER vinder, så en langsom genhentning ikke
  // blinker «tom» forbi. Derefter FEJL, så et gammelt resultat ikke skjuler
  // at det nye kald slog fejl.
  if (henter && antal === 0) {
    return (
      <div className="liste-tilstand henter" role="status" aria-live="polite">
        <Loader2 size={14} className="liste-tilstand-spin" aria-hidden="true" />
        <span>Henter…</span>
      </div>
    )
  }
  if (fejl) {
    return (
      <div className="liste-tilstand fejl" role="status">
        <AlertTriangle size={14} aria-hidden="true" />
        <span className="liste-tilstand-tekst">{fejl}</span>
        {onIgen && (
          <button type="button" className="liste-tilstand-igen" onClick={onIgen}>
            Prøv igen
          </button>
        )}
      </div>
    )
  }
  if (antal === 0) {
    return (
      <div className="liste-tilstand tom">
        <Inbox size={14} aria-hidden="true" />
        <span>{tomTekst}</span>
      </div>
    )
  }
  return <>{children}</>
}
