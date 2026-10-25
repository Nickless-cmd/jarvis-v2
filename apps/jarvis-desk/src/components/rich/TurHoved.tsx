/**
 * Turens hoved — den ENESTE vandrette streg i samtalen.
 *
 * ## Hvorfor den er delt
 *
 * Code mode og chat mode havde hver sin implementering. Chat-modens var en bar
 * `<div>` uden streg, uden shimmer og uden fold-pil, så de to visninger drev
 * fra hinanden i det øjeblik de blev bygget (målt 17/10-2026: chat viste
 * `.chat-flow-activity`, code viste `.rv-tur`). Bjørn valgte at de skal dele
 * komponenten, ikke bare ligne hinanden — så de ikke KAN divergere igen.
 *
 * ## Kontrakten
 *
 * Højde 33px, en reserveret 1px skillelinje, tekst i `--rv-tertiary` og
 * fold-pilen i `--fg-3`. Shimmeren er `rv-glimt-tekst` gennem `.shimmer` plus
 * det lyse SVG-lag i pilen, styret af `data-koerer` — præcis som før.
 */
import type { ReactNode, Ref } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { formaterTurTid } from '../../lib/turTid'
import { RullendeTid } from './RullendeTid'
import '../../styles/turhoved.css'

/** Fold-pilen. Et RIGTIGT ikon — ikke teksttegnet ▸/▾ (Bjørn 23/9-2026:
 *  «slippe for ▸ som ikon og så bare bruge den rigtige >»).
 *
 *  Retningen skiftes ved at BYTTE ikonet frem for at rotere det, så stregen
 *  står skarp i begge tilstande — samme greb som forlægget
 *  (DisclosureRow.tsx:68: `leading = open ? <Chevron/> : icon`). */
export function FoldPil({ aaben, className }: { aaben: boolean; className?: string }) {
  return aaben
    ? <ChevronDown className={className} size={14} strokeWidth={1.75} />
    : <ChevronRight className={className} size={14} strokeWidth={1.75} />
}

export interface TurHovedProps {
  /** Linjen der står i hovedet. Klippes med ellipse — ombrydes aldrig. */
  tekst: string
  aaben: boolean
  onToggle: () => void
  /** Tænder shimmer i tekst og pil. Kalderen bestemmer hvornår. */
  koerer?: boolean
  /** Turens forløbne sekunder. Vises som `42s` / `1m 5s`; `null` = intet ur. */
  sekunder?: number | null
  /** Levende metadata efter teksten, fx code-turens rullende token-tal. */
  meta?: ReactNode
  /** Om skillestregen under hovedet er kommet til syne. Hovedets plads er
   *  uændret mens stregen glider ind, så `Working` kan stå der fra turstart. */
  skillelinje?: boolean
  /** Om der er noget at folde. `false` = hovedet er kun en skillestreg med
   *  uret, og fold-pilen skjules, så den ikke lover et indhold der ikke er der
   *  (Bjørn 17/10-2026: hovedet skal stå der også på ture uden værktøjskald). */
  foldbar?: boolean
  knapRef?: Ref<HTMLButtonElement>
}

export function TurHoved({
  tekst, aaben, onToggle, koerer = false, sekunder = null, meta,
  skillelinje = true, foldbar = true, knapRef,
}: TurHovedProps) {
  const tilstand = {
    ...(koerer ? { 'data-koerer': '' } : {}),
    ...(skillelinje ? { 'data-skillelinje': '' } : {}),
  }
  const indhold = (
    <>
      {/* ÉT shimmerfelt over tekst + metadata + ur. Tre `.shimmer`-børn gav
          tre samtidige lysbånd; nu fortsætter det samme bånd gennem linjen. */}
      <span className={`rv-turIndhold${koerer ? ' shimmer' : ''}`}>
        <span className="rv-turTekst">{tekst}</span>
        {meta}
        {typeof sekunder === 'number' ? (
          <RullendeTid tekst={formaterTurTid(sekunder)} />
        ) : null}
      </span>
      {foldbar ? (
        <span className="rv-turC" aria-hidden="true">
          <FoldPil aaben={aaben} />
          <FoldPil aaben={aaben} className="rv-ikon-glimt" />
        </span>
      ) : null}
    </>
  )

  // Uden indhold at folde er hovedet ikke en knap. En knap der ikke gør noget
  // er en løgn i tabulatorrækkefølgen — samme streg, ingen affordance.
  if (!foldbar) {
    return (
      <div className="rv-tur rv-tur--statisk" {...tilstand}>
        {indhold}
      </div>
    )
  }

  return (
    <button
      type="button"
      ref={knapRef}
      className="rv-tur"
      aria-expanded={aaben}
      {...tilstand}
      onClick={onToggle}
    >
      {indhold}
    </button>
  )
}
