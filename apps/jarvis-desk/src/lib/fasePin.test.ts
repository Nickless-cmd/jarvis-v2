import { describe, it, expect } from 'vitest'
import { faseForsinkelse, faseStil } from './fasePin'

/**
 * Fire loaders monteret paa fire tidspunkter puster forskudt. Det ser forkert
 * ud paa en maade der er svaer at pege paa (spec punkt 8).
 */

describe('fase-pinning', () => {
  it('to elementer monteret på FORSKELLIGE tidspunkter får samme fase', () => {
    // Det er hele pointen. 1400ms-cyklus: et element monteret ved 300ms og et
    // ved 1700ms står samme sted i cyklussen, og skal derfor have samme
    // forsinkelse.
    expect(faseForsinkelse(1400, 300)).toBe(faseForsinkelse(1400, 1700))
    expect(faseForsinkelse(1400, 300)).toBe('-300ms')
  })

  it('forsinkelsen er NEGATIV — en positiv ville lade loaderen stå stille', () => {
    for (const nu of [1, 700, 1399, 99999]) {
      expect(Number(faseForsinkelse(1400, nu).replace('ms', ''))).toBeLessThanOrEqual(0)
    }
  })

  it('præcis ved cyklussens start er forsinkelsen 0', () => {
    expect(faseForsinkelse(1400, 0)).toBe('0ms')
    expect(faseForsinkelse(1400, 2800)).toBe('0ms')
  })

  it('en NEGATIV klokke giver stadig en negativ forsinkelse', () => {
    // Et enkelt modulo ville give en positiv forsinkelse her, og så stod
    // loaderen stille indtil uret havde indhentet den.
    expect(faseForsinkelse(1000, -250)).toBe('-750ms')
  })

  it('en ugyldig varighed giver 0ms, ikke NaN', () => {
    // `animation-delay: NaNms` er ugyldig og får HELE deklarationen til at
    // falde bort — altså ingen animation overhovedet.
    for (const v of [0, -5, Number.NaN, Number.POSITIVE_INFINITY]) {
      expect(faseForsinkelse(v, 500), String(v)).toBe('0ms')
    }
  })

  it('faseStil er klar til at sættes på et element', () => {
    expect(faseStil(1400, 300)).toEqual({ animationDelay: '-300ms' })
  })

  it('uden et `nu` bruger den urets egen tid — og giver stadig et gyldigt tal', () => {
    const v = faseForsinkelse(1400)
    expect(v).toMatch(/^-?\d+(\.\d+)?ms$/)
    expect(Number(v.replace('ms', ''))).toBeGreaterThan(-1400)
  })
})
