/**
 * Rullende tal — turens ur som mekanik, ikke som tekst.
 *
 * Bjørn 17/10-2026: «tallende skal rulle nedfra og op». Hvert ciffer er sin
 * egen lodrette strimmel med 0-9 stablet, og det aktive ciffer skubbes ind i
 * viewporten. Når 9 → 0 ruller det NEDAD (fremad), aldrig tilbage — derfor
 * `translateY(-ciffer * 1em)` og ikke en rotation.
 *
 * ## Hvorfor ikke bare animere hele strengen
 *
 * `12s` → `13s` er ét ciffer der skifter. Ruller man hele strengen, danser
 * `1` og `s` med, og uret ser uroligt ud i stedet for præcist. Kun de cifre
 * der faktisk ændrer sig bevæger sig.
 *
 * ## Bredden
 *
 * Hver strimmel er `1ch` bred med `tabular-nums`, så de enkelte cifre ikke
 * ændrer bredde. Tidsled har ingen indledende nuller (`1m 5s`).
 */
import { memo } from 'react'

/** Ét ciffer som lodret strimmel. `key` på værdien får React til at genstarte
 *  transitionen, så samme ciffer to gange i træk ikke animerer forgæves. */
const Ciffer = memo(function Ciffer({ tegn }: { tegn: string }) {
  const tal = Number(tegn)
  if (!Number.isInteger(tal)) {
    // `m`, `s`, `t` og mellemrum ruller ikke — de står stille.
    return <span className="rv-turTidFast">{tegn}</span>
  }
  return (
    <span className="rv-turTidCiffer" aria-hidden="true">
      <span className="rv-turTidStrimmel" style={{ transform: `translateY(${-tal}em)` }}>
        {[0, 1, 2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
          <span key={n}>{n}</span>
        ))}
      </span>
    </span>
  )
})

/** Hele tidsstrengen, ciffer for ciffer. Skærmlæsere får den flade tekst. */
export const RullendeTid = memo(function RullendeTid({ tekst }: { tekst: string }) {
  return (
    <span className="rv-turTid" role="timer" aria-label={tekst}>
      <span aria-hidden="true">
        {[...tekst].map((tegn, i) => (
          <Ciffer key={`${i}-${tegn}`} tegn={tegn} />
        ))}
      </span>
    </span>
  )
})
