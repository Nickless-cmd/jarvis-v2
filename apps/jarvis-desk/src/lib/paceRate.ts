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

/** Efterslæbet fordeles over så mange sekunder. Uændret fra 20/10 — det er
 *  dét der gør at pacen ikke kan komme bagud: rate ≥ pending / 3. */
export const PACE_CATCH_UP_SECONDS = 3

/** Sikkerhedsloft. Højt nok til at 2000 tegn indhentes på ~3 s (667 tegn/s)
 *  og lavt nok til at et absurd target stadig fordeles over tid. */
export const PACE_LOFT = 4000

export interface RateInput {
  /** Hvor mange kodepunkter der mangler at blive vist. */
  pending: number
  /** Forrige rates værdi — glatningen bærer historikken. */
  forrigeRate: number
  /** Målt ankomst i kodepunkter/s siden sidste frame. `null` = intet nyt
   *  delta i denne frame, så ankomsten må ikke opdateres. */
  ankomst: number | null
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
export function naesteRate({ pending, forrigeRate, ankomst }: RateInput): number {
  if (pending <= 0) return PACE_GULV

  // 1. Følg kilden. Uden et nyt delta står målingen stille — et svar der er
  //    færdigankommet må ikke få sin rate nulstillet midt i udrulningen.
  let rate = forrigeRate
  if (ankomst !== null && Number.isFinite(ankomst) && ankomst > 0) {
    rate = PACE_EMA * ankomst + (1 - PACE_EMA) * rate
  }

  // 2. Grundtempoet er et GULV, ikke et mål.
  rate = Math.max(PACE_GULV, rate)

  // 3. Indhentningskravet — dét der gør at pacen ikke KAN komme bagud.
  //    Ved 2000 tegn giver det 667 tegn/s: målt 2,50 s mod 15,07 s med det
  //    gamle faste loft på 180.
  rate = Math.max(rate, pending / PACE_CATCH_UP_SECONDS)

  // 4. Sikkerhedsloftet er en nødudgang, ikke den bindende grænse.
  return Math.min(PACE_LOFT, rate)
}
