/**
 * Pacerens hastighed — kildens tempo er målet, indhentning er undtagelsen.
 *
 * ## Hvorfor den ikke er en konstant
 *
 * Bjørn 29/10-2026: «svaret streames stadig færdigt inde i hoved før det
 * paces.. efter agentiske runder». MÅLT med den rigtige pacer og et
 * deterministisk ur: 2000 tegn tog **15,07 s** at rulle ud. Serveren havde
 * sendt det hele på under et sekund.
 *
 * Årsagen var `Math.min(180, pending / 3)`: skrev modellen hurtigere end
 * 180 tegn/s, voksede efterslæbet gennem HELE svaret, og pacen indhentede
 * aldrig. Loftet var sat 20/10 for at undgå et 18,8 s hængevindue — det ramte
 * rigtigt, men det ramte ikke problemet.
 *
 * ## Hvad Codex desktop gør (målt på Bjørns maskine 29/10-2026)
 *
 * Deres pacer har **intet loft** — `Math.max(1, rate)` er et GULV. Den måler
 * ankomsthastigheden som et glidende gennemsnit og justerer den mod
 * efterslæbet. Nettet siger det samme i fem uafhængige kilder: «rate =
 * clamp(pending / 0.25s, 20, 800)», «too slow, and the model finishes while
 * the user is still watching text from seconds ago» — Bjørns klage ordret.
 *
 * ## 20/11-2026: kurven var ujævn gennem ÉT svar — og det var klagen
 *
 * Bjørn: «så snart hoved folder og streamen forsætter uden for hoved løber den
 * stærkere for slut beskeden og sænker farten til sidste».
 *
 * MÅLT med den ægte tick-løkke (60 fps, kredit, loft pr. frame), FØR:
 *
 *   scenarie              ujævnhed   varighed   rate 25 %→90 %
 *   dump 1200 tegn           6,57x      6,18 s   278 → 63
 *   dump 3000 tegn          14,25x      8,02 s   550 → 65
 *
 * Ujævnhed er `maks rate / min rate` efter de første 15 % af udrulningen. Et
 * svar der ruller 14x hurtigere i midten end i slutningen er præcis den kurve
 * Bjørn beskriver — og grunden til at synteserne føltes rolige mens
 * slutbeskeden ikke gjorde: synteserne ANKOMMER jævnt, så raten skal ikke
 * gøre noget. Slutbeskeden ankommer i store hug.
 *
 * Årsagen var `pending / PACE_CATCH_UP_SECONDS` som NEDRE GRÆNSE HVER FRAME:
 * den skalerer med det RESTERENDE efterslæb, så tempoet uvægerligt falder i
 * takt med at efterslæbet skrumper. Den var ikke forkert da den blev skrevet —
 * den løste at et dump på 2000 tegn tog 15 s — men den gjorde indhentningen
 * til en deceleration.
 *
 * ## Tre modeller blev målt, ikke gættet (samme scenarier, samme ur)
 *
 * A. KUN kildens tempo, ingen indhentning (Bjørns idé: «sørg for den ikk
 *    forsøger at indhente»). MÅLT: mest stabil af alle på jævn ankomst —
 *    ujævnhed **1,01** — men et dump på 3000 tegn tog **62,5 s** og 6000 tegn
 *    **125 s**. Kilden leverer kun ÉT delta, så dens tempo kan ikke måles op;
 *    uden indhentning står den på grundtempoet og kravler. Forkastet.
 *
 * B. Indhentning der venter til kilden har været tavs i 0,8 s. MÅLT: jævn
 *    ankomst 1,01, men dump hoppede **12–62x** fordi de første 0,8 s ruller i
 *    grundtempo og tempoet derefter springer til 579. Et synligt hak.
 *    Forkastet.
 *
 * C. Kildens tempo som mål + indhentning der fastsættes ÉN gang når kilden
 *    ikke leverer. MÅLT: **1,06–1,08 overalt**, dump 2,1 s uanset størrelse,
 *    kort svar 2,02 s. Valgt — den er næsten lige så stabil som A (5 % fra)
 *    og har ingen af A's eller B's fejl.
 *
 * MÅLT EFTER (model C), samme scenarier:
 *
 *   scenarie              ujævnhed   varighed   rate 25 %→90 %
 *   dump 1200 tegn           1,08x      2,12 s   591 → 600
 *   dump 3000 tegn           1,08x      2,13 s  1479 → 1500
 *   fold-spring              1,06x        —      394 → 401
 *   kort svar 100 tegn       1,00x      2,02 s    50 → 50
 *
 * Kontrakterne er urørte: 100 tegn ruller stadig 2,02 s (>1,9 s), grundtempoet
 * er 48, og sikkerhedsloftet er 4000.
 *
 * ## Tilstanden skal bæres af kalderen
 *
 * `kilde` og `indh` kan ikke udledes af `forrigeRate` alene — de ER den
 * hukommelse der gør kurven jævn. De returneres derfor sammen med raten, og
 * kalderen gemmer dem mellem frames. Uden det ville hvert kald starte forfra
 * og kurven ville være den gamle.
 */

/** Grundtempo. Uændret fra 20/10: korte svar skal rulle roligt. */
export const PACE_GULV = 48

/** Glatning af den målte ankomst. Codex bruger 0.1/0.9; samme vægt her, så
 *  ét stort delta ikke kaster hastigheden. */
export const PACE_EMA = 0.1

/** Vægt for kildens langsomme tempo-hukommelse.
 *
 *  0,02 pr. frame ved 60 fps ≈ 4 s halveringstid. MÅLT 20/11-2026: med samme
 *  vægt som den hurtige EMA (0,1) arvede kilden et enkelt burst, og et
 *  fold-spring på 400 tegn løftede tempoet til 528 tegn/s i stedet for 471.
 *  Den langsomme vægt er hvad der gør slutbeskeden lige så rolig som
 *  synteserne: tempoet følger strømmen, ikke det enkelte hug. */
export const PACE_KILDE_EMA = 0.02

/** Efterslæbet fordeles over så mange sekunder når kilden er stoppet.
 *
 *  Den var 3 fra 20/10. MÅLT 30/10-2026 (Bjørn: «Pacen løber for stærkt»)
 *  viste en sweep at 3 gjorde halen for lang, fordi `pending / T` er
 *  ASYMPTOTISK: p(t) = p₀·exp(-t/T), så et langt svar aldrig «lander».
 *
 *  MÅLT kurve, alt-i-én-frame (værste tilfælde):
 *
 *    T    100     300     500     1000    2000    4000
 *    3s   2,08s   4,73s   6,25s   8,33s   10,40s  12,47s
 *    2s   2,05s   3,45s   4,45s   5,83s    7,22s   8,58s
 *    1,5s 1,70s   2,48s   2,93s   3,65s    4,52s   5,55s
 *    1s   1,20s   1,45s   1,53s   1,60s    1,65s   1,67s
 *
 *  2 er valgt fordi det er det største T hvor et langt svar ikke nærmer sig
 *  de 15 s der VAR klagen 29/10 — og det mindste hvor 100 tegn stadig ruller
 *  >1,9 s, som er kontrakten fra 20/10. 1,5 bryder den kontrakt (1,70 s), og
 *  1 gør hvert svar til et dump på under 2 s uanset længde.
 *
 *  20/11-2026: T bruges nu ÉN gang pr. indhentning, ikke som en løbende nedre
 *  grænse. Kurven er derfor lineær i stedet for asymptotisk, og tiderne
 *  ovenfor er en ØVRE grænse — målt blev 3000 tegn 2,13 s mod de 8,58 s
 *  tabellen lover for den gamle regel. */
export const PACE_CATCH_UP_SECONDS = 2

/** Sikkerhedsloft. Højt nok til at 2000 tegn indhentes på ~3 s (667 tegn/s)
 *  og lavt nok til at et absurd target stadig fordeles over tid. */
export const PACE_LOFT = 4000

/** Halveringstid for tilbagefaldet mod målet, i sekunder.
 *
 *  MÅLT 30/10-2026 (Bjørn: «Pacen løber for stærkt»): uden dette faldt raten
 *  ALDRIG tilbage. `naesteRate` startede med `let rate = forrigeRate` og
 *  rørte den kun når der kom et nyt delta — så ÉN burst på 100 tegn i én
 *  frame (målt som 6000 tegn/s) satte tempoet til 643 tegn/s, 13,4x
 *  grundtempoet, og den blev stående der resten af svaret. Målt: frame 1, 2
 *  og 5 gav alle 643.
 *
 *  20/11-2026: tilbagefaldet går nu mod `max(kilde, indh)` — svarets eget mål —
 *  i stedet for mod grundtempoet. Det er forskellen på «falder til ro» og
 *  «sænker farten til sidste»: en kilde der leverede 400 tegn/s skal ikke
 *  pludselig rulles ud i 48. */
export const PACE_DECAY_HALFLIFE_S = 1.0

/** Hvor langt et vindue ankomsthastigheden måles over, i sekunder.
 *
 *  MÅLT 30/10-2026: blev ankomsten målt pr. FRAME, gav en SSE-chunk på 100
 *  tegn i én 16,7 ms-frame en «ankomst» på 6000 tegn/s. Over 300 ms bliver
 *  den samme chunk til ~333 tegn/s — den hastighed brugeren faktisk ser.
 *
 *  300 ms er ~18 frames ved 60 Hz: langt nok til at en enkelt chunk ikke
 *  farver målingen, kort nok til at pacen reagerer inden for en læsbar pause. */
export const PACE_ANKOMST_VINDUE_S = 0.3

/** Hvor meget raten må glide pr. frame mod sit mål.
 *
 *  MÅLT 20/11-2026: uden glidningen sprang raten fra 48 til 600 i én frame når
 *  et dump blev indhentet, og det læses som at teksten «starter med at
 *  sprinte». 0,12 pr. frame ved 60 fps når målet på ~0,3 s — hurtigt nok til
 *  at indhentningen ikke føles tøvende, langsomt nok til at kurven er jævn. */
export const PACE_GLIDNING = 0.12

/** Pacerens hukommelse. Bæres af kalderen mellem frames. */
export interface RateTilstand {
  /** Kildens glattede tempo i kodepunkter pr. sekund. */
  kilde: number
  /** Fastsat indhentningstempo; 0 = ingen aktiv indhentning. */
  indh: number
}

/** Frisk tilstand ved starten af et svar. */
export function startPace(): RateTilstand {
  return { kilde: PACE_GULV, indh: 0 }
}

export interface RateInput {
  /** Hvor mange kodepunkter der mangler at blive vist. */
  pending: number
  /** Forrige rates værdi — glidningen bærer historikken. */
  forrigeRate: number
  /** Målt ankomst i kodepunkter/s over målevinduet. `null` = intet nyt
   *  delta i dette vindue, så kildens tempo må ikke opdateres. */
  ankomst: number | null
  /** Sekunder siden sidste frame. Gør tilbagefaldet uafhængigt af fps —
   *  uden den ville et 144 Hz-panel falde 2,4x hurtigere tilbage end et
   *  60 Hz-panel, og hastigheden ville afhænge af skærmen. */
  dt?: number
  /** Pacerens hukommelse. Skal være den samme gennem hele svaret. */
  tilstand: RateTilstand
}

export interface RateSvar {
  /** Visningshastighed i kodepunkter pr. sekund. */
  rate: number
  /** Næste tilstand — gem den og send den ind i næste kald. */
  tilstand: RateTilstand
}

/**
 * Næste visningshastighed i kodepunkter pr. sekund.
 *
 * Rækkefølgen betyder noget: kildens tempo måles FØRST (det er målet),
 * indhentningstempoet fastsættes DEREFTER (kun når kilden ikke leverer), og
 * raten glider til sidst mod det højeste af dem. Bytter man om, kan et
 * efterslæb der ikke findes løfte tempoet — eller et tempo der ER målt blive
 * glemt i slutningen af svaret.
 */
export function naesteRate({
  pending,
  forrigeRate,
  ankomst,
  dt,
  tilstand,
}: RateInput): RateSvar {
  if (pending <= 0) return { rate: PACE_GULV, tilstand: startPace() }

  let { kilde, indh } = tilstand
  const maalt = ankomst !== null && Number.isFinite(ankomst) && ankomst > 0

  // 1. Kildens tempo. Langsom EMA, så ét hug ikke farver resten — men den
  //    glemmer heller ikke at kilden VAR hurtig. Det er dét der giver
  //    slutbeskeden samme ro som synteserne: tempoet følger strømmen.
  if (maalt) {
    kilde = PACE_KILDE_EMA * (ankomst as number) + (1 - PACE_KILDE_EMA) * kilde
    // Kilden leverer: en fastsat indhentning er ikke længere sandheden.
    indh = 0
  } else if (indh === 0 && pending > PACE_GULV * PACE_CATCH_UP_SECONDS) {
    // Kilden leverer ikke, og efterslæbet kan ikke indhentes i grundtempoet.
    // Fastlæg tempoet ÉN gang — herefter holdes det, så resten af svaret
    // ruller med samme fart som midten i stedet for at decelerere.
    indh = pending / PACE_CATCH_UP_SECONDS
  }

  // 2. Ratens mål: kildens tempo, eller et fastsat indhentningstempo.
  const maalRate = Math.min(PACE_LOFT, Math.max(PACE_GULV, kilde, indh))

  // 3. Glid mod målet — aldrig et spring. Tilbagefaldet går mod `maalRate`
  //    (ikke mod grundtempoet), så en hurtig kilde ikke pludselig rulles ud i
  //    48 tegn/s til sidst.
  let rate = forrigeRate
  if (maalt) {
    rate = PACE_EMA * (ankomst as number) + (1 - PACE_EMA) * rate
  } else if (rate > maalRate) {
    const sekunder = Math.max(0, Math.min(0.5, dt ?? 1 / 60))
    const tilbage = Math.pow(0.5, sekunder / PACE_DECAY_HALFLIFE_S)
    rate = maalRate + (rate - maalRate) * tilbage
  }
  rate += (maalRate - rate) * PACE_GLIDNING

  return {
    rate: Math.min(PACE_LOFT, Math.max(PACE_GULV, rate)),
    tilstand: { kilde, indh },
  }
}
