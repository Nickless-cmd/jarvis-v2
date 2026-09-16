import { useState } from 'react'
import { useLoebendeTid } from '../../lib/useLoebendeTid'
import { Brain, ChevronDown, ChevronRight } from 'lucide-react'
import { MarkdownRenderer } from './MarkdownRenderer'

/**
 * Tænkningen som ÉN linje — søskende til runde-linjen, 1:1 med mobilens
 * `ThinkingSummary`.
 *
 *     🧠 Tænker · 4 s           (mens den tænker — tallet løber)
 *     🧠 Tænkte i 12 s  ›       (bagefter — klik folder tanken ud)
 *
 * Bjørn 16/9-2026: «lige nu vises fuld tænker output på skærmen.. i mobil er
 * det lige som tool results linjen. Live meta data og kollaps for at se
 * indholdet». Før strømmede hele monologen ind i tråden mens han tænkte og
 * forsvandt sporløst bagefter.
 *
 * Under KORT_TAERSKEL_S vises intet tal — mobilens måling (1.511 blokke, 67 %
 * under 3 s) viste at den gentagne talrække var støjen, ikke linjen.
 */
export const KORT_TAERSKEL_S = 3

export function ThinkingLine({
  text,
  seconds,
  live,
}: {
  text: string
  /** Målt varighed fra serveren (gemte beskeder). */
  seconds?: number
  /** Tænker lige NU. */
  live: boolean
}) {
  const [open, setOpen] = useState(false)
  // Live tæller linjen selv — se useLoebendeTid. Serverens måling vinder.
  const loebende = useLoebendeTid(live)
  const harTekst = text.trim().length > 0
  const sek = live ? loebende : seconds ?? loebende
  if (!live && !harTekst && sek == null) return null

  const label = live
    // Hele sekunder live: «1,2 s … 1,3 s» ville flimre hvert tick.
    ? `Tænker${sek != null && sek >= 1 ? ` · ${Math.floor(sek)} s` : ''}`
    : sek != null && sek >= KORT_TAERSKEL_S
      ? `Tænkte i ${formatSek(sek)}`
      : 'Tænkte'
  const Chevron = open ? ChevronDown : ChevronRight

  return (
    <div className={`toolgroup tanke-linje${live ? ' er-koerende' : ''}`}>
      <button
        type="button"
        className="toolgroup-head"
        aria-expanded={harTekst ? open : undefined}
        disabled={!harTekst}
        onClick={() => setOpen((o) => !o)}
      >
        <Brain size={15} className="toolgroup-icon" strokeWidth={1.8} />
        <span className="toolgroup-label">{label}</span>
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
