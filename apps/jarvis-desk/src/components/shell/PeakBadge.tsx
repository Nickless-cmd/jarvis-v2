import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../lib/api'
import { apiFetch } from '../../lib/api'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'

/** Myldretids-badge (30/9-2026, Bjørns bestilling).
 *
 *  DeepSeek fakturerer det DOBBELTE i myldretiden (UTC 01-04 + 06-10, man-fre).
 *  Badgen har fire tilstande:
 *    · skjult  — off-peak, mere end 15 min til vinduet (headeren er stille)
 *    · varsel  — ≤ 15 min før: gul pille, pulserende prik, mm:ss nedtælling
 *    · aktiv   — inde i vinduet: rød pille, «1t 47m» til det lukker
 *    · efter   — ~2 min efter luk: kort grøn «✓ off-peak», så væk igen
 *
 *  Sandheden om VINDUERNE kommer fra /peak/state (som læser MYLDRE_VINDUER i
 *  llm_pricing.py — defineret ét sted). Nedtællingen tælles LOKALT hvert
 *  sekund, så vi ikke poller hvert sekund.
 *
 *  Den BLOKERER intet. Husets mønster er at vagter observerer, ikke afviser.
 */
interface PeakState {
  ok: boolean
  in_peak: boolean
  now_danish?: string | null
  peak_starts_danish?: string | null
  peak_ends_danish?: string | null
  minutes_left?: number | null
  next_peak_danish?: string | null
  minutes_until_next?: number | null
}

const VARSEL_MIN = 15
const EFTER_MS = 2 * 60 * 1000

function mmss(sek: number): string {
  const m = Math.floor(sek / 60)
  const s = sek % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function varighed(min: number): string {
  if (min < 60) return `${min} min`
  const t = Math.floor(min / 60)
  const m = min % 60
  return m ? `${t}t ${m}m` : `${t}t`
}

export function PeakBadge({ config }: { config?: ApiConfig }) {
  const { data } = usePollWhenVisible<PeakState>(
    () => apiFetch<PeakState>(config!, '/peak/state'),
    60_000,
    !!config,
  )
  // Lokal nedtælling — ét sekund, uden at polle.
  const [nu, setNu] = useState(() => Date.now())
  const [efterTil, setEfterTil] = useState<number | null>(null)

  useEffect(() => {
    const t = setInterval(() => setNu(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])

  // Fang overgangen aktiv → off-peak, så «✓ off-peak» kan vises kort.
  const [varIPeak, setVarIPeak] = useState(false)
  useEffect(() => {
    if (!data) return
    if (data.in_peak) {
      setVarIPeak(true)
      setEfterTil(null)
    } else if (varIPeak) {
      setVarIPeak(false)
      setEfterTil(Date.now() + EFTER_MS)
    }
  }, [data, varIPeak])

  if (!data || !data.ok) return null

  // ── aktiv ──────────────────────────────────────────────────────────────
  if (data.in_peak) {
    const minTilbage = data.minutes_left ?? 0
    return (
      <div
        className="peak-badge tone-peak"
        title={`Myldretid — DeepSeek koster 2×. Lukker ${data.peak_ends_danish ?? '?'} dansk. Bjørns ture kører; tungt baggrundsarbejde kan vente.`}
      >
        <span className="peak-dot" />
        <span className="peak-label">myldretid</span>
        <span className="peak-count">{varighed(minTilbage)}</span>
      </div>
    )
  }

  // ── efter (kort grøn kvittering) ───────────────────────────────────────
  if (efterTil && nu < efterTil) {
    return (
      <div className="peak-badge tone-off" title="Myldretiden er lukket — normal pris igen.">
        <span className="peak-dot" />
        <span className="peak-label">off-peak</span>
      </div>
    )
  }

  // ── varsel (≤ 15 min før) ──────────────────────────────────────────────
  const mangler = data.minutes_until_next
  if (mangler != null && mangler <= VARSEL_MIN) {
    const sek = Math.max(0, mangler * 60 - Math.floor((nu % 60000) / 1000))
    return (
      <div
        className="peak-badge tone-varsel"
        title={`Myldretid om ${mangler} min (${data.next_peak_danish ?? '?'} dansk). Tungt arbejde der kan klares nu, bør klares nu.`}
      >
        <span className="peak-dot pulse" />
        <span className="peak-label">myldretid om</span>
        <span className="peak-count">{mmss(sek)}</span>
      </div>
    )
  }

  // ── skjult ─────────────────────────────────────────────────────────────
  return null
}
