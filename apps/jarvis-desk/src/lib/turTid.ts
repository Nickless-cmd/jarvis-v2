/**
 * Turens ur.
 *
 * ## Hvorfor det ikke bor i komponenten
 *
 * Et ur der starter ved MONTERING måler hvor længe komponenten har været på
 * skærmen — ikke hvor længe turen har kørt. Chat-visningen bliver gen-monteret
 * når man skifter session og igen når den levende besked afløses af den
 * persisterede, og så ville tiden starte forfra midt i en tur.
 *
 * Starttidspunktet kommer derfor fra stream-tilstanden (`StreamState.turStart`,
 * sat ved `message_start`), og dette modul tæller kun op fra det.
 *
 * ## Formen
 *
 * Bjørn 17/10-2026: «timer for turen Xm Xs startende med Xs og så Xm osv» —
 * sekunder alene indtil det første minut, derefter minutter og sekunder.
 */
import { useEffect, useRef, useState } from 'react'

/** `12s` → `1m 05s` → `1t 04m`. Sekund-delen er altid to cifre efter et minut,
 *  så tallet ikke hopper i bredden hvert sekund. */
export function formaterTurTid(sekunder: number): string {
  const hel = Math.max(0, Math.floor(sekunder))
  if (hel < 60) return `${hel}s`
  const minutter = Math.floor(hel / 60)
  if (minutter < 60) return `${minutter}m ${String(hel % 60).padStart(2, '0')}s`
  return `${Math.floor(minutter / 60)}t ${String(minutter % 60).padStart(2, '0')}m`
}

/**
 * Turens forløbne sekunder, talt op fra `start`.
 *
 * Fryser når `loeber` bliver falsk — så den afsluttede besked viser turens
 * samlede tid i stedet for at tælle videre for evigt.
 */
export function useTurSekunder(
  start: number | null | undefined,
  loeber: boolean,
): number | null {
  const [nu, setNu] = useState(() => Date.now())
  const frosset = useRef<number | null>(null)

  useEffect(() => {
    if (loeber) {
      frosset.current = null
      setNu(Date.now())
      const id = setInterval(() => setNu(Date.now()), 1000)
      return () => clearInterval(id)
    }
    // Netop afsluttet: lås tidspunktet, så tallet står stille resten af visningen.
    if (frosset.current === null) frosset.current = Date.now()
    return undefined
  }, [loeber])

  if (typeof start !== 'number' || !Number.isFinite(start)) return null
  const slut = loeber ? nu : (frosset.current ?? nu)
  return Math.max(0, Math.round((slut - start) / 1000))
}
