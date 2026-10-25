/**
 * Rullende tal — turens ur som mekanik, ikke som tekst.
 *
 * Bjørn 17/10-2026 og 25/10-2026: «tallende skal rulle nedfra og op».
 * Turhovedet deler nu hjulmekanik med rundetimeren: det gamle ciffer glider
 * op og ud, mens det nye kommer ind nedefra. Det gælder også 9 → 0.
 *
 * ## Hvorfor ikke bare animere hele strengen
 *
 * `12s` → `13s` er ét ciffer der skifter. Ruller man hele strengen, danser
 * `1` og `s` med, og uret ser uroligt ud i stedet for præcist. Kun de cifre
 * der faktisk ændrer sig bevæger sig.
 *
 * ## Bredden
 *
 * Hvert hjul er breddefast med `tabular-nums`, så de enkelte cifre ikke
 * ændrer bredde. Tidsled har ingen indledende nuller (`1m 5s`). Den delte
 * mekanik holder desuden cifrene på fontens ægte baseline.
 */
import { memo } from 'react'
import { RullendeCifre } from '../feedback/RullendeTal'

/** Hele tidsstrengen, ciffer for ciffer. Skærmlæsere får den flade tekst. */
export const RullendeTid = memo(function RullendeTid({
  tekst,
  className = '',
}: {
  tekst: string
  className?: string
}) {
  return (
    <span className={`rv-turTid rullende${className ? ` ${className}` : ''}`} role="timer" aria-label={tekst}>
      <span className="rv-turTidHjul" aria-hidden="true">
        <RullendeCifre tekst={tekst} retning="op" />
      </span>
    </span>
  )
})
