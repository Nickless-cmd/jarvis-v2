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
 * ## Hvorfor det også har en sluttid
 *
 * Første udgave frøs uret når `aktiv` blev falsk — men `aktiv` betyder «kører
 * og har ikke svaret endnu», så uret stoppede i det øjeblik Jarvis begyndte at
 * svare, altså MIDT i turen. Bjørn 17/10-2026: «ueret skal osse når strømmen er
 * forbi». Nu fryser det på `turSlut`, som sættes ved `message_stop` — turens
 * faktiske afslutning — og bliver stående i hovedet bagefter.
 *
 * ## Formen
 *
 * Bjørn 17/10-2026: «timer for turen Xm Xs startende med Xs og så Xm osv» —
 * sekunder alene indtil det første minut, derefter minutter og sekunder.
 */
import { useEffect, useState } from 'react'

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
 * Turens forløbne sekunder, talt op fra `start` og frosset ved `slut`.
 *
 * `slut` er turens afslutning (`message_stop`), ikke «svaret begyndte». Er den
 * sat, står tallet stille — også efter genindlæsning, hvis kalderen kan give
 * begge tidspunkter med.
 */
export function useTurSekunder(
  start: number | null | undefined,
  slut: number | null | undefined,
): number | null {
  const [nu, setNu] = useState(() => Date.now())
  const loeber = typeof slut !== 'number'

  useEffect(() => {
    if (!loeber) return undefined
    setNu(Date.now())
    const id = setInterval(() => setNu(Date.now()), 1000)
    return () => clearInterval(id)
  }, [loeber])

  if (typeof start !== 'number' || !Number.isFinite(start)) return null
  const ende = typeof slut === 'number' && Number.isFinite(slut) ? slut : nu
  return Math.max(0, Math.round((ende - start) / 1000))
}

/**
 * Turens varighed udledt af transskriptet, når stream-tilstanden ikke har den.
 *
 * Den persisterede besked bærer ingen varighed, men hver `tool`-række har en
 * `created_at`. Spændet fra brugerens besked til den sidste værktøjsrække er
 * turens faktiske længde — minus det sidste modelsvar, som ikke har et
 * tidsstempel. Det er tæt nok til at uret kan stå der også efter genindlæsning,
 * og det er ærligt: hellere et let undervurderet tal end intet ur.
 */
export function varighedFraBesked(
  beskedTid: string | null | undefined,
  sidsteVaerktoejTid: string | null | undefined,
): number | null {
  if (!beskedTid || !sidsteVaerktoejTid) return null
  const start = Date.parse(beskedTid)
  const slut = Date.parse(sidsteVaerktoejTid)
  if (!Number.isFinite(start) || !Number.isFinite(slut) || slut < start) return null
  return Math.round((slut - start) / 1000)
}
