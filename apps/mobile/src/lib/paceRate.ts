/**
 * Pacerens hastighed på mobilen — målt mod ankomsten, ikke klippet af et loft.
 *
 * ## Hvorfor denne fil findes
 *
 * Desk har haft modellen siden 29/10-2026. Mobilen har haft sine egne to
 * kopier, og begge bar den fejl desk fjernede:
 *
 *   · `usePacedBlocks` (code): `step = min(28, …)` pr. 33 ms-tick = 848
 *     tegn/s, et hårdt loft der ikke kan indhente et efterslæb.
 *   · `useChatPacedBlocks` (chat): `Math.min(180, pending / 3)` — ordret det
 *     loft desk fjernede 29/10.
 *
 * MÅLT 18/11-2026 med den ægte kurve på begge flader: 2000 tegn der ankommer
 * i én frame tog **3,00 s** på mobil mod **0,58 s** på desk (5,15x), og 5000
 * tegn tog **6,53 s** selv om alt allerede var ankommet. Det er præcis Bjørns
 * klage fra 29/10: «svaret streames stadig færdigt inde i hoved før det
 * paces». Forskellen er strukturel — et loft kan per definition ikke indhente.
 *
 * ## Modellen
 *
 * Fire trin, og rækkefølgen betyder noget: ankomsten glattes FØRST (den måler
 * kilden), grundtempoet løfter den DEREFTER (det er gulvet), og
 * indhentningskravet sætter til sidst den nedre grænse der gør at pacen ikke
 * kan være bagud. Bytter man om på de to sidste, kan grundtempoet tabe til et
 * efterslæb der ikke findes.
 *
 * Filen er en tro port af `apps/jarvis-desk/src/lib/paceRate.ts`. De to apps
 * deler ingen kode i dag (ingen `shared/`, ingen tsconfig-paths, ingen
 * metro-`watchFolders`), så det er en kopi — og den skal holdes i takt.
 */

/** Grundtempo. Korte svar skal rulle roligt, ikke blinke frem. */
export const PACE_GULV = 48

/** Glatning af den målte ankomst, så ét stort delta ikke kaster hastigheden. */
export const PACE_EMA = 0.1

/** Efterslæbet fordeles over så mange sekunder.
 *
 *  `pending / T` er ASYMPTOTISK: p(t) = p₀·exp(-t/T), så et langt svar aldrig
 *  «lander». Målt på desk 30/10-2026: T=3 gjorde halen for lang (2000 tegn =
 *  10,40 s), T=1 gjorde hvert svar til et dump. 2 er det største T hvor et
 *  langt svar ikke nærmer sig de 15 s der VAR klagen — og det mindste hvor 100
 *  tegn stadig ruller >1,9 s. */
export const PACE_CATCH_UP_SECONDS = 2

/** Sikkerhedsloft — en nødudgang, ikke den bindende grænse. */
export const PACE_LOFT = 4000

/** Halveringstid for tilbagefaldet mod grundtempoet, i sekunder.
 *
 *  Uden den blev ÉN burst stående resten af svaret: målt på desk satte en
 *  chunk på 100 tegn i én frame tempoet til 643 tegn/s, og det faldt aldrig
 *  tilbage. 1,0 s halverer et burst-tempo på ét sekund og gør det praktisk
 *  talt væk efter tre. */
export const PACE_DECAY_HALFLIFE_S = 1.0

/** Hvor langt et vindue ankomsthastigheden måles over, i sekunder.
 *
 *  Målt pr. FRAME blev en chunk på 100 tegn i én 16,7 ms-frame til 6000
 *  tegn/s — ikke 100 tegn. Over 300 ms bliver den samme chunk til ~333
 *  tegn/s, som er den hastighed brugeren faktisk ser. */
export const PACE_ANKOMST_VINDUE_S = 0.3

export interface RateInput {
  /** Hvor mange kodepunkter der mangler at blive vist. */
  pending: number
  /** Forrige rates værdi — glatningen bærer historikken. */
  forrigeRate: number
  /** Målt ankomst i kodepunkter/s over målevinduet. `null` = intet nyt
   *  delta, så ankomsten må ikke opdateres. */
  ankomst: number | null
  /** Sekunder siden sidste frame. Gør tilbagefaldet uafhængigt af fps —
   *  uden den ville et 120 Hz-panel falde dobbelt så hurtigt tilbage som et
   *  60 Hz-panel, og hastigheden ville afhænge af skærmen. */
  dt?: number
}

/**
 * Næste visningshastighed i kodepunkter pr. sekund.
 *
 * Kan ikke komme bagud: indhentningskravet er en NEDRE grænse, ikke et loft.
 */
export function naesteRate({ pending, forrigeRate, ankomst, dt }: RateInput): number {
  if (pending <= 0) return PACE_GULV

  // 1. Følg kilden. Kommer der et nyt delta, glattes det ind. Kommer der
  //    INTET nyt, fryser vi ikke — raten glider tilbage mod grundtempoet, så
  //    én burst ikke sætter tempoet for resten af svaret.
  let rate = forrigeRate
  if (ankomst !== null && Number.isFinite(ankomst) && ankomst > 0) {
    rate = PACE_EMA * ankomst + (1 - PACE_EMA) * rate
  } else if (rate > PACE_GULV) {
    const sekunder = Math.max(0, Math.min(0.5, dt ?? 1 / 60))
    const tilbage = Math.pow(0.5, sekunder / PACE_DECAY_HALFLIFE_S)
    rate = PACE_GULV + (rate - PACE_GULV) * tilbage
  }

  // 2. Grundtempoet er et GULV, ikke et mål.
  rate = Math.max(PACE_GULV, rate)

  // 3. Indhentningskravet — dét der gør at pacen ikke KAN komme bagud.
  rate = Math.max(rate, pending / PACE_CATCH_UP_SECONDS)

  // 4. Sikkerhedsloftet er en nødudgang, ikke den bindende grænse.
  return Math.min(PACE_LOFT, rate)
}
