import { describe, expect, it } from 'vitest'
import { beregnFjederkurve, fjederTilCss } from './fjeder'

describe('fjederkurve', () => {
  it('dæmper oversvingene og lander præcis på slutværdien', () => {
    const kurve = beregnFjederkurve({
      stiffness: 320,
      damping: 18,
      mass: 1,
      velocity: 0,
    })

    expect(kurve.vaerdier[0]).toBe(0)
    expect(kurve.vaerdier.some((vaerdi) => vaerdi > 1)).toBe(true)

    const vendepunkter = kurve.vaerdier.slice(1, -1).filter((vaerdi, indeks, alle) => {
      const foer = alle[indeks - 1] ?? kurve.vaerdier[0]!
      const efter = alle[indeks + 1] ?? kurve.vaerdier.at(-1)!
      return (vaerdi > foer && vaerdi > efter) || (vaerdi < foer && vaerdi < efter)
    })
    const afvigelser = vendepunkter.map((vaerdi) => Math.abs(1 - vaerdi))
    expect(afvigelser.length).toBeGreaterThanOrEqual(2)
    expect(afvigelser.every((afvigelse, indeks) => indeks === 0 || afvigelse < afvigelser[indeks - 1]!))
      .toBe(true)
    expect(kurve.vaerdier.at(-1)).toBe(1)
  })

  it('leverer en CSS-kurve og en positiv, fysikafledt varighed', () => {
    const css = fjederTilCss({ stiffness: 320, damping: 18, mass: 1, velocity: 0 })
    expect(css.easing).toMatch(/^linear\(0(?:\.0+)?, /)
    expect(css.easing).toMatch(/1\)$/)
    expect(css.durationMs).toBeGreaterThan(0)
  })
})
