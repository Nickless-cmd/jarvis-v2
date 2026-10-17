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
 * Højde 33px, `border-bottom: .5px solid var(--line)`, tekst i `--rv-tertiary`
 * og fold-pilen i `--fg-3`. Shimmeren er `rv-glimt-tekst` gennem `.shimmer`
 * plus det lyse SVG-lag i pilen, styret af `data-koerer` — præcis som før.
 */
import type { Ref } from 'react'
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
  /** Turens forløbne sekunder. Vises som `· 42s` / `· 1m 05s`; `null` = intet ur. */
  sekunder?: number | null
  knapRef?: Ref<HTMLButtonElement>
}

export function TurHoved({ tekst, aaben, onToggle, koerer = false, sekunder = null, knapRef }: TurHovedProps) {
  return (
    <button
      type="button"
      ref={knapRef}
      className="rv-tur"
      aria-expanded={aaben}
      {...(koerer ? { 'data-koerer': '' } : {})}
      onClick={onToggle}
    >
      <span className={`rv-turTekst${koerer ? ' shimmer' : ''}`}>{tekst}</span>
      {typeof sekunder === 'number' ? (
        <RullendeTid tekst={formaterTurTid(sekunder)} />
      ) : null}
      <span className="rv-turC" aria-hidden="true">
        <FoldPil aaben={aaben} />
        <FoldPil aaben={aaben} className="rv-ikon-glimt" />
      </span>
    </button>
  )
}
