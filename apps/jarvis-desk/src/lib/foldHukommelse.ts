/**
 * Turens fold-tilstand, husket på beskedens identitet — ikke på komponentens.
 *
 * ## Hullet (målt 30/10-2026, `foldRemount.maaling.test.tsx`)
 *
 * `aabenManuelt` var `useState<boolean|null>` inde i komponenten. Målt:
 *
 *   rerender uden remount  → tilstanden overlevede (React holder state)
 *   remount                → NULSTILLET, på begge flader
 *
 * Remountet rammer ikke sjældent: den levende tur er en BETINGET søskende uden
 * key, mens de historiske rækker ligger i et `.map` med `key={m.id}`. Når
 * streamen slutter, afmonteres den levende række og en NY monteres. Brugeren
 * havde foldet ud for at se arbejdet — og folden sprang tilbage.
 *
 * Codex-appen (målt samme dag) har ikke problemet: deres
 * `chatgpt-reasoning-group` har en STABIL identitet
 * (`` `${kildemessageId}:${indeks}` ``) brugt som React-key, så samme instans
 * overlever at items bliver spillet igen. Det er dét vi mangler.
 *
 * ## Løsningen
 *
 * Tilstanden flyttes UD af instansen og ind i en Map keyed på beskedens
 * identitet. Ved remount læses den gemte værdi i `useState`'s initializer, så
 * den nye instans starter hvor den gamle slap.
 *
 * Nøglen er `runId ?? beskedId`. `runId` er den FÆLLES nøgle: den levende række
 * har `activeRunId`, og den persisterede besked bærer `run_id` — «run'et der
 * skrev beskeden» (`ChatMessage.run_id`, `core/services/besked_run_kobling.py`).
 * Derfor overlever folden også selve overgangen live → persisteret, ikke kun et
 * remount inden for samme fase.
 *
 * ## Uden nøgle huskes intet
 *
 * Er nøglen `undefined` (fx en komponent testet isoleret), falder hooken
 * tilbage til ren lokal state. Det er med vilje: uden en identitet findes der
 * intet at binde tilstanden til, og så må den opføre sig som før. Det er den
 * adfærd `foldRemount.maaling.test.tsx` dokumenterer.
 *
 * ## Loftet
 *
 * Mappen lever så længe browserfanen gør. Uden et loft voksede den med hver
 * besked brugeren foldede i, gennem en hel arbejdsdag. `MAKS_POSTER` holder den
 * flad ved at kaste den ældst rørte post ud — samme form som en LRU.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

/** Hvor mange beskeder vi husker folden for. Rigeligt for en session. */
export const MAKS_POSTER = 200

const hukommelse = new Map<string, boolean>()

/** Læs en gemt fold-tilstand. `undefined` = brugeren har ikke rørt den. */
export function laesFold(noegle: string): boolean | undefined {
  const vaerdi = hukommelse.get(noegle)
  if (vaerdi === undefined) return undefined
  // LRU: flyt til slutningen, så den ikke ryger først ud.
  hukommelse.delete(noegle)
  hukommelse.set(noegle, vaerdi)
  return vaerdi
}

/** Gem en fold-tilstand på dens nøgle og hold mappen under loftet. */
export function skrivFold(noegle: string, vaerdi: boolean): void {
  hukommelse.delete(noegle)
  hukommelse.set(noegle, vaerdi)
  while (hukommelse.size > MAKS_POSTER) {
    const aeldste = hukommelse.keys().next()
    if (aeldste.done) break
    hukommelse.delete(aeldste.value)
  }
}

/** Tøm hukommelsen. Kun til test — produktionskoden har ingen grund til det. */
export function rydFoldHukommelse(): void {
  hukommelse.clear()
}

/** Antal huskede beskeder. Bruges af testen til at måle loftet. */
export function foldHukommelseStoerrelse(): number {
  return hukommelse.size
}

/**
 * Fold-tilstand bundet til en besked-identitet.
 *
 * Returnerer `[tilstand, saetTilstand]` hvor `tilstand === null` betyder «ikke
 * rørt» — kalderen falder så tilbage på sin egen standard (typisk «kører
 * arbejdet?»). Det bevarer den eksisterende semantik i begge flader.
 */
export function useFoldHukommelse(
  noegle: string | undefined,
): readonly [boolean | null, (vaerdi: boolean) => void] {
  const [manuelt, setManuelt] = useState<boolean | null>(
    () => (noegle ? laesFold(noegle) ?? null : null),
  )
  // Nøglen kan skifte uden remount: den levende række får `activeRunId`, og når
  // den persisteres, står det samme id i `run_id`. Skifter nøglen til noget
  // ANDET, hører tilstanden til en anden besked og skal nulstilles.
  const noegleRef = useRef(noegle)
  useEffect(() => {
    if (noegleRef.current === noegle) return
    noegleRef.current = noegle
    setManuelt(noegle ? laesFold(noegle) ?? null : null)
  }, [noegle])

  const saet = useCallback((vaerdi: boolean) => {
    setManuelt(vaerdi)
    if (noegle) skrivFold(noegle, vaerdi)
  }, [noegle])

  return [manuelt, saet] as const
}
