import {
  naesteRate,
  PACE_GULV,
  PACE_CATCH_UP_SECONDS,
  PACE_LOFT,
  PACE_EMA,
} from './paceRate'

/**
 * Kontrakten, ikke implementeringen.
 *
 * Hver test er mutationsprøvet — se `MUT`-noterne: den adfærd testen påstår
 * at måle er slået fra, og testen er set fejle. Den vigtigste er «kan ikke
 * komme bagud»: det er hele grunden til at filen findes, og det er præcis
 * den egenskab de to gamle mobil-pacere manglede.
 */

const FPS = 60
const FRAME_S = 1 / FPS
/** Samme loft pr. frame som chat-hooket bruger. */
const MAX_FRAME_DELTA_S = 0.1

/**
 * Simulér den ægte kredit-løkke fra `useChatPacedBlocks`: rate fra
 * `naesteRate`, kredit der akkumulerer `rate × dt`, og et trin pr. frame.
 *
 * `ankomst` er `null` fordi hele svaret lander i én frame FØR løkken starter —
 * det er værste tilfælde, og det er det tilfælde de gamle pacere fejlede på.
 */
function tidTilUdruulning(total: number): number {
  let vist = 0
  let rate = PACE_GULV
  let kredit = 0
  let frames = 0
  const maksFrames = 60 * 120
  while (vist < total && frames < maksFrames) {
    const pending = total - vist
    rate = naesteRate({ pending, forrigeRate: rate, ankomst: null, dt: FRAME_S })
    const maksPrFrame = Math.max(6, Math.ceil(rate * MAX_FRAME_DELTA_S))
    kredit = Math.min(maksPrFrame, kredit + rate * FRAME_S)
    const step = Math.min(maksPrFrame, Math.floor(kredit))
    if (step > 0) {
      kredit -= step
      vist = Math.min(total, vist + step)
    }
    frames++
  }
  return frames * FRAME_S
}

describe('naesteRate', () => {
  it('har et grundtempo som GULV — et kort svar må ikke blinke frem', () => {
    // MUT: returnér `pending / PACE_CATCH_UP_SECONDS` uden `Math.max(PACE_GULV, …)`
    //      → 10 tegn giver 5 tegn/s → fanger.
    expect(naesteRate({ pending: 10, forrigeRate: PACE_GULV, ankomst: null })).toBeGreaterThanOrEqual(
      PACE_GULV,
    )
  })

  it('indhenter et stort efterslæb — raten er pending/T, ikke et loft', () => {
    // MUT: genindfør et loft på 180 (`Math.min(180, rate)`) → 2000/2 = 1000
    //      bliver 180 → fanger. Det er ordret den gamle mobil-fejl.
    expect(naesteRate({ pending: 2000, forrigeRate: PACE_GULV, ankomst: null })).toBe(
      2000 / PACE_CATCH_UP_SECONDS,
    )
  })

  it('kan ikke komme bagud: 25x mere tekst koster logaritmisk, ikke lineært', () => {
    // Modellen er ASYMPTOTISK (p(t) = p₀·e^(-t/T)), så tiden vokser med
    // ln(størrelse) — ikke med størrelsen. Det er hele forskellen fra et loft:
    // det gamle `min(28, …)` gav 848 tegn/s, altså LINEÆR tid, og et svar der
    // var 25x større tog 25x længere.
    //
    // MUT: genindfør et loft (`Math.min(180, rate)`) → 5000 tegn tager ~28 s
    //      ved 180 tegn/s → fanger.
    const lille = tidTilUdruulning(200)
    const stor = tidTilUdruulning(5000)
    expect(stor / lille).toBeLessThan(4)
    expect(stor).toBeLessThan(10)
  })

  it('glatter ankomsten, så ét stort delta ikke kaster hastigheden', () => {
    // MUT: `rate = ankomst` i stedet for EMA → 6000 tegn/s i første frame →
    //      fanger.
    const rate = naesteRate({ pending: 100, forrigeRate: PACE_GULV, ankomst: 6000 })
    expect(rate).toBeLessThan(6000)
    expect(rate).toBeCloseTo(PACE_EMA * 6000 + (1 - PACE_EMA) * PACE_GULV, 5)
  })

  it('falder tilbage mod grundtempoet når intet nyt ankommer', () => {
    // MUT: fjern `else if`-grenen → raten bliver stående på 1000 → fanger.
    // Det var fejlen 30/10-2026: én burst satte tempoet resten af svaret.
    let rate = 1000
    for (let i = 0; i < 120; i++) {
      rate = naesteRate({ pending: 3000, forrigeRate: rate, ankomst: null, dt: FRAME_S })
    }
    // Efter 2 s (to halveringstider) skal burst-tempoet være praktisk talt væk.
    // Gulvet og indhentningskravet (3000/2 = 1500) sætter stadig en bund.
    expect(rate).toBeLessThan(1600)
  })

  it('har et sikkerhedsloft der ikke kan nås i praksis', () => {
    // MUT: fjern `Math.min(PACE_LOFT, rate)` → 100.000 tegn giver 50.000
    //      tegn/s → fanger.
    expect(naesteRate({ pending: 100_000, forrigeRate: PACE_GULV, ankomst: null })).toBe(PACE_LOFT)
  })

  it('går tilbage til grundtempoet når der intet venter', () => {
    // MUT: returnér `forrigeRate` ved pending <= 0 → en afsluttet udrulning
    //      står tilbage i høj hastighed til næste svar → fanger.
    expect(naesteRate({ pending: 0, forrigeRate: 3000, ankomst: 500 })).toBe(PACE_GULV)
  })
})
