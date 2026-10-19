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
import type { ContentBlock } from './sseProtocol'

/** `12s` → `1m 5s` → `1t 4m`. Ingen indledende nuller: hvert tidsled skrives
 *  som et almindeligt tal, også lige efter minut- og timeskiftet. */
export function formaterTurTid(sekunder: number): string {
  const hel = Math.max(0, Math.floor(sekunder))
  if (hel < 60) return `${hel}s`
  const minutter = Math.floor(hel / 60)
  if (minutter < 60) return `${minutter}m ${hel % 60}s`
  return `${Math.floor(minutter / 60)}t ${minutter % 60}m`
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

/** Summen af modellens faktiske thinking-blokke — ikke turens væg-ur.
 * Afsluttede blokke bærer `seconds`; den ene åbne blok tælles fra `startet`.
 * Mangler udbyderen thinking-blokke, returneres `null` frem for et opdigtet
 * tal baseret på hele turen (som også indeholder tools og svarskrivning). */
export function beregnTankeSekunder(
  blocks: readonly ContentBlock[],
  nu = Date.now(),
): number | null {
  let sekunder = 0
  let harTanke = false
  for (const block of blocks) {
    if (!block || block.type !== 'thinking') continue
    harTanke = true
    if (typeof block.seconds === 'number' && Number.isFinite(block.seconds)) {
      sekunder += Math.max(0, block.seconds)
    } else if (typeof block.startet === 'number' && Number.isFinite(block.startet)) {
      sekunder += Math.max(0, (nu - block.startet) / 1000)
    }
  }
  return harTanke ? Math.max(0, Math.floor(sekunder)) : null
}

/** Levende thinking-tid. Uret kører kun mens en thinking-blok er åben; under
 * tool-kald står tallet stille, selv om turens samlede ur fortsætter. */
export function useTankeSekunder(blocks: readonly ContentBlock[]): number | null {
  const [nu, setNu] = useState(() => Date.now())
  const tankeAaben = blocks.some((block) => block?.type === 'thinking'
    && block.seconds == null && block.startet != null)

  useEffect(() => {
    if (!tankeAaben) return undefined
    setNu(Date.now())
    const id = setInterval(() => setNu(Date.now()), 1000)
    return () => clearInterval(id)
  }, [tankeAaben])

  return beregnTankeSekunder(blocks, nu)
}

/**
 * Turens varighed udledt af transskriptet, når stream-tilstanden ikke har den.
 *
 * Den persisterede besked bærer ingen varighed — men den skrives ved turens
 * SLUTNING, og brugerens besked skrives ved dens START. Spændet mellem de to
 * rækkers `created_at` er derfor hele turen, målt på serveren.
 *
 * Målt mod databasen 17/10-2026 på tre vilkårlige ture: 3m26s, 26s og 7s —
 * tal der matcher hvad der faktisk blev observeret i UI'et. Den tidligere
 * variant målte til sidste værktøjsrække og undervurderede systematisk, fordi
 * det afsluttende modelsvar ikke har et tidsstempel.
 */
export function varighedFraTider(
  brugerTid: string | null | undefined,
  assistentTid: string | null | undefined,
): number | null {
  if (!brugerTid || !assistentTid) return null
  const start = Date.parse(brugerTid)
  const slut = Date.parse(assistentTid)
  if (!Number.isFinite(start) || !Number.isFinite(slut) || slut < start) return null
  const sekunder = Math.round((slut - start) / 1000)
  // En tur der løber over to timer er ikke en tur — det er et genoptaget run
  // eller et ur der lyver. Hellere intet tal end et forkert.
  return sekunder > 0 && sekunder < 7200 ? sekunder : null
}
