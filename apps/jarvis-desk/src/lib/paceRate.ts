/**
 * Pacerens hastighed — målt mod ankomsten, ikke klippet af et fast loft.
 *
 * ## Hvorfor den ikke er en konstant
 *
 * Bjørn 29/10-2026: «svaret streames stadig færdigt inde i hoved før det
 * paces.. efter agentiske runder». MÅLT med den rigtige pacer og et
 * deterministisk ur: 2000 tegn tog **15,07 s** at rulle ud. Serveren havde
 * sendt det hele på under et sekund.
 *
 * Årsagen var ikke grundtempoet. Den var `Math.min(180, pending / 3)`:
 * skrev modellen hurtigere end 180 tegn/s, voksede efterslæbet gennem HELE
 * svaret, og pacen indhentede aldrig. Loftet var sat 20/10 for at undgå et
 * 18,8 s hængevindue — det ramte rigtigt, men det ramte ikke problemet.
 *
 * ## Hvad Codex desktop gør (målt på Bjørns maskine 29/10-2026)
 *
 * Deres pacer har **intet loft** — `Math.max(1, rate)` er et GULV. Den måler
 * ankomsthastigheden som et glidende gennemsnit og justerer den mod
 * efterslæbet. Bliver backloggen stor, hæves hastigheden indtil den er
 * indhentet: den KAN ikke komme bagud. Nettet siger det samme i fem
 * uafhængige kilder: «rate = clamp(pending / 0.25s, 20, 800)», «too slow, and
 * the model finishes while the user is still watching text from seconds ago»
 * — som er Bjørns klage ordret.
 *
 * ## Hvad vi beholder fra vores egen
 *
 * 1. **Gulvet.** Codex har 1; vi har 48. Et kort svar skal ikke blinke frem,
 *    og et svar der lander i ét hug skal stadig rulle roligt. Det er
 *    grundtempoet fra 20/10 og det røres ikke.
 * 2. **Indhentningskravet.** `pending / 3` — uændret fra 20/10. Det er den
 *    regel der gør at pacen ikke kan være bagud. Det var kun LOFTET over den
 *    der var forkert.
 * 3. **Et sikkerhedsloft der ikke kan nås i praksis.** Uden nogen grænse
 *    kunne et korrupt target på 100.000 tegn give et hak.
 *
 * ## Hvad jeg prøvede og forkastede
 *
 * Jeg overførte Codex' to relative grene direkte:
 *
 *   if (pending < rate * 1.5) rate = (pending + rate * 1.5) / 2
 *   if (pending > rate / 1.2) rate = (pending + rate / 1.2) / 2
 *
 * MÅLT: ved 100 tegn og rate 48 er `pending > rate / 1.2`, så hastigheden blev
 * hævet til 70 fra første frame. Et kort svar rullede dermed 1,22 s hvor
 * kontrakten kræver >1,9 s — 40 % for hurtigt, i det tilfælde hvor der slet
 * ikke ER et efterslæb at indhente. Grenene måler backlog relativt til en rate
 * der selv er ved at blive målt; vores grundtempo er absolut, og de to kan
 * ikke forenes uden at grundtempoet taber.
 *
 * Den adaptive del der ER værd at beholde er glatningen af ankomsten: uden
 * den hopper rate fra frame til frame når et delta lander i én stor bid.
 */

/** Grundtempo. Uændret fra 20/10: korte svar skal rulle roligt. */
export const PACE_GULV = 48

/** Glatning af den målte ankomst. Codex bruger 0.1/0.9; samme vægt her, så
 *  ét stort delta ikke kaster hastigheden. */
export const PACE_EMA = 0.1

/** Efterslæbet fordeles over så mange sekunder.
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
 *  1 gør hvert svar til et dump på under 2 s uanset længde. */
export const PACE_CATCH_UP_SECONDS = 2

/** Sikkerhedsloft. Højt nok til at 2000 tegn indhentes på ~3 s (667 tegn/s)
 *  og lavt nok til at et absurd target stadig fordeles over tid. */
export const PACE_LOFT = 4000

/** Halveringstid for tilbagefaldet mod grundtempoet, i sekunder.
 *
 *  MÅLT 30/10-2026 (Bjørn: «Pacen løber for stærkt»): uden dette faldt raten
 *  ALDRIG tilbage. `naesteRate` startede med `let rate = forrigeRate` og
 *  rørte den kun når der kom et nyt delta — så ÉN burst på 100 tegn i én
 *  frame (målt som 6000 tegn/s) satte tempoet til 643 tegn/s, 13,4x
 *  grundtempoet, og den blev stående der resten af svaret. Målt: frame 1, 2
 *  og 5 gav alle 643.
 *
 *  1,0 s betyder at et burst-tempo er halveret efter ét sekund og praktisk
 *  talt væk efter tre. Det er langsomt nok til at et svar der ankommer i
 *  bølger stadig føles jævnt, og hurtigt nok til at et afsluttet burst ikke
 *  farver resten af udrulningen.
 *
 *  Tilbagefaldet kan ALDRIG sænke pacen under indhentningskravet — trin 3
 *  nedenfor sætter den nedre grænse, så et reelt efterslæb indhentes stadig. */
export const PACE_DECAY_HALFLIFE_S = 1.0

/** Hvor langt et vindue ankomsthastigheden måles over, i sekunder.
 *
 *  MÅLT 30/10-2026: blev ankomsten målt pr. FRAME, gav en SSE-chunk på 100
 *  tegn i én 16,7 ms-frame en «ankomst» på 6000 tegn/s. Over 300 ms bliver
 *  den samme chunk til ~333 tegn/s — den hastighed brugeren faktisk ser.
 *
 *  Vinduet er også hvad der gør et burst-mønster og et jævnt mønster med
 *  SAMME gennemsnit tilnærmelsesvis ens: målt uden vindue gav jævn ankomst
 *  600 tegn/s en rate på 600, mens burst gav 4000 (sikkerhedsloftet).
 *
 *  300 ms er ~18 frames ved 60 Hz: langt nok til at en enkelt chunk ikke
 *  farver målingen, kort nok til at pacen reagerer inden for en læsbar pause. */
export const PACE_ANKOMST_VINDUE_S = 0.3

export interface RateInput {
  /** Hvor mange kodepunkter der mangler at blive vist. */
  pending: number
  /** Forrige rates værdi — glatningen bærer historikken. */
  forrigeRate: number
  /** Målt ankomst i kodepunkter/s over målevinduet. `null` = intet nyt
   *  delta i denne frame, så ankomsten må ikke opdateres. */
  ankomst: number | null
  /** Sekunder siden sidste frame. Gør tilbagefaldet uafhængigt af fps —
   *  uden den ville et 144 Hz-panel falde 2,4x hurtigere tilbage end et
   *  60 Hz-panel, og hastigheden ville afhænge af skærmen. */
  dt?: number
}

/**
 * Næste visningshastighed i kodepunkter pr. sekund.
 *
 * Rækkefølgen betyder noget: ankomsten glattes FØRST (den er et mål for
 * kilden), grundtempoet løfter den DEREFTER (det er gulvet), og
 * indhentningskravet sætter til sidst den nedre grænse der gør at pacen ikke
 * kan være bagud. Bytter man om på de to sidste, kan grundtempoet tabe til
 * et efterslæb der ikke findes.
 */
export function naesteRate({ pending, forrigeRate, ankomst, dt }: RateInput): number {
  if (pending <= 0) return PACE_GULV

  // 1. Følg kilden. Kommer der et nyt delta, glattes det ind. Kommer der
  //    INTET nyt, måler vi ikke — men vi fryser heller ikke. Raten glider
  //    tilbage mod grundtempoet med en halveringstid, så én burst ikke
  //    sætter tempoet for resten af svaret (målt 30/10-2026: den blev
  //    stående på 643 tegn/s, 13,4x grundtempoet, i alle efterfølgende
  //    frames).
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
  //    Ved 2000 tegn giver det 667 tegn/s: målt 2,50 s mod 15,07 s med det
  //    gamle faste loft på 180. Det er også dét der gør tilbagefaldet i
  //    trin 1 sikkert: et reelt efterslæb kan ikke dø hen.
  rate = Math.max(rate, pending / PACE_CATCH_UP_SECONDS)

  // 4. Sikkerhedsloftet er en nødudgang, ikke den bindende grænse.
  return Math.min(PACE_LOFT, rate)
}
