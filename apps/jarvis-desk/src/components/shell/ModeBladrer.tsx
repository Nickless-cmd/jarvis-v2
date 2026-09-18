import { ChevronLeft, ChevronRight } from 'lucide-react'
import { MODES, NAVN, type Mode } from './ModeDropdown'

/**
 * To pile der bladrer mellem Chat, Arbejde og Code (Bjørn 18/9-2026).
 *
 * Dropdown'en ved siden af svarer på «hvor er jeg, og hvor kan jeg komme hen»
 * og koster et klik plus et sigte. Pilene svarer på «den ved siden af» og
 * koster ét klik uden at ramme noget. De to ting er ikke i vejen for hinanden:
 * dropdown'en er til at springe, pilene er til at bladre.
 *
 * Cyklisk med vilje. Et bladre-greb med ender kræver at man ved hvor man står
 * i rækken før man trykker — og så er det ikke længere et bladre-greb.
 */
export function ModeBladrer({
  active,
  onChange,
}: {
  active: Mode
  onChange: (m: Mode) => void
}) {
  const plads = MODES.indexOf(active)
  // Ukendt mode → behandl som første, så pilene aldrig står døde.
  const nr = plads < 0 ? 0 : plads
  // `noUncheckedIndexedAccess` gør et tuple-opslag til `T | undefined`, også når
  // modulo-regningen gør det umuligt. Ét sted at falde tilbage frem for to
  // udråbstegn — så en tom MODES ville give 'chat', ikke en kørselsfejl.
  const ved = (i: number): Mode => MODES[((i % MODES.length) + MODES.length) % MODES.length] ?? 'chat'
  const forrige = ved(nr - 1)
  const naeste = ved(nr + 1)

  return (
    <div className="mode-bladrer" role="group" aria-label="Bladr mellem tilstande">
      <button
        type="button"
        className="icon-btn"
        title={`Forrige: ${NAVN[forrige]}`}
        aria-label={`Forrige tilstand: ${NAVN[forrige]}`}
        onClick={() => onChange(forrige)}
      >
        <ChevronLeft size={15} />
      </button>
      <button
        type="button"
        className="icon-btn"
        title={`Næste: ${NAVN[naeste]}`}
        aria-label={`Næste tilstand: ${NAVN[naeste]}`}
        onClick={() => onChange(naeste)}
      >
        <ChevronRight size={15} />
      </button>
    </div>
  )
}
