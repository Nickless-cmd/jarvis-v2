import { useState } from 'react'
import { useLoebendeTid } from '../../lib/useLoebendeTid'
import { tankeFragment } from '../../lib/tankeFragment'
import { prikker, usePrikTrin } from '../../lib/prikSekvens'
import { Brain, ChevronDown, ChevronRight } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'

/**
 * Tænkningen som ÉN linje — søskende til runde-linjen, 1:1 med mobilens
 * `ThinkingSummary`.
 *
 *     🧠 Tænker · 4 s · Lad mig se hvor værnet sidder…   (live)
 *     🧠 Tænkte i 12 s  ›                                (bagefter)
 *
 * Bjørn 16/9-2026: «lige nu vises fuld tænker output på skærmen.. i mobil er
 * det lige som tool results linjen. Live meta data og kollaps for at se
 * indholdet». 17/9-2026: linjen skal også vise hvad han tænker PÅ mens den
 * løber — mobilen har det over skrivefeltet, desk på selve linjen.
 *
 * Tiden kommer fra BLOKKEN (`startet`/`seconds`), ikke fra komponenten. Før
 * forsvandt «Tænkte i xx s» nogle gange: linjen blev monteret om da runderne
 * blev grupperet, og et ur født ved montering startede forfra.
 *
 * Tallet vises ALTID når det er målt. Før skjulte vi det under 3 s (mobilens
 * måling: 67 % af tankerne var så korte), men Bjørn 17/9-2026 så netop det som
 * at tiden «ikke var persistet» efter turen: live stod der «Tænker · 7 s», og
 * den gemte besked der overtog sagde bare «Tænkte».
 */
export const KORT_TAERSKEL_S = 0

export function ThinkingLine({
  text,
  seconds,
  live,
  startet,
}: {
  text: string
  /** Målt varighed: serverens (gemt) eller reducerens (live, når tanken sluttede). */
  seconds?: number
  /** Tænker lige NU. */
  live: boolean
  /** Klientens ur da tanken startede. */
  startet?: number
}) {
  const [open, setOpen] = useState(false)
  const loebende = useLoebendeTid(live, startet)
  const trin = usePrikTrin(live)
  const harTekst = text.trim().length > 0
  const sek = live ? loebende : seconds ?? loebende
  if (!live && !harTekst && sek == null) return null

  const label = live
    ? `Tænker${prikker(trin)}`
    : sek != null && sek > KORT_TAERSKEL_S
      ? `Tænkte i ${formatSek(sek)}`
      : 'Tænkte'
  // Live: tiden og hvad han tænker på, dæmpet efter ordet. Hele sekunder:
  // «1,2 s … 1,3 s» ville flimre hvert tick.
  const liveMeta = live
    ? [sek != null && sek >= 1 ? `${Math.floor(sek)} s` : '', tankeFragment(text)].filter(Boolean)
    : []
  const Chevron = open ? ChevronDown : ChevronRight

  return (
    <div className={`toolgroup tanke-linje${live ? ' er-koerende' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={harTekst ? open : undefined}
        aria-label={live ? 'Tænker' : label}
        disabled={!harTekst}
        onClick={() => setOpen((o) => !o)}
      >
        <Brain size={15} className="toolgroup-icon" strokeWidth={1.8} />
        <span className="toolgroup-label">
          <span className="linje-titel">{label}</span>
          {liveMeta.length ? <span className="linje-meta" data-testid="tanke-meta"> · {liveMeta.join(' · ')}</span> : null}
        </span>
        {harTekst ? <Chevron size={15} className="toolgroup-chevron" strokeWidth={1.8} /> : null}
      </button>
      {open && harTekst ? (
        <div className="tanke-body">
          <MarkdownRenderer text={text} streaming={live} />
        </div>
      ) : null}
    </div>
  )
}

/** 12 → «12 s», 3,4 → «3,4 s», 75 → «1 min 15 s». Dansk komma. */
export function formatSek(s: number): string {
  if (s >= 60) return `${Math.floor(s / 60)} min ${Math.round(s % 60)} s`
  const r = s >= 10 ? Math.round(s) : Math.round(s * 10) / 10
  return `${String(r).replace('.', ',')} s`
}
