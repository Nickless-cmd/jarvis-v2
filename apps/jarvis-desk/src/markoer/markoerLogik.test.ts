import { describe, expect, it } from 'vitest'
import {
  FADE_MS,
  MIN_AFSTAND,
  TRAIL_MAKS,
  fjernAeldre,
  opacitet,
  sporStoerrelse,
  tilfoejPeg,
  type Peg,
} from './markoerLogik'

const peg = (id: number, x: number, y: number, t = 0): Peg => ({ id, x, y, t })

describe('tilfoejPeg', () => {
  it('lægger et punkt til listen', () => {
    const liste = tilfoejPeg([], peg(1, 10, 20, 5))
    expect(liste).toEqual([peg(1, 10, 20, 5)])
  })

  it('springer en mikro-bevægelse over og giver SAMME liste tilbage', () => {
    const foerste = tilfoejPeg([], peg(1, 10, 20))
    const anden = tilfoejPeg(foerste, peg(2, 10 + MIN_AFSTAND - 1, 20))
    // Identitet, ikke blot lighed: kalderen bruger det til at springe en
    // unødig React-render over.
    expect(anden).toBe(foerste)
  })

  it('tager en bevægelse på præcis tærsklen med', () => {
    const foerste = tilfoejPeg([], peg(1, 10, 20))
    const anden = tilfoejPeg(foerste, peg(2, 10 + MIN_AFSTAND, 20))
    expect(anden).toHaveLength(2)
  })

  it('holder listen nede på maks og dropper den ældste', () => {
    let liste: Peg[] = []
    for (let i = 0; i < TRAIL_MAKS + 5; i++) {
      liste = tilfoejPeg(liste, peg(i, i * 50, 0))
    }
    expect(liste).toHaveLength(TRAIL_MAKS)
    expect(liste[0]?.id).toBe(5)
    expect(liste[liste.length - 1]?.id).toBe(TRAIL_MAKS + 4)
  })

  it('rører ikke input-listen (ingen mutation)', () => {
    const foerste = [peg(1, 0, 0)]
    tilfoejPeg(foerste, peg(2, 100, 100))
    expect(foerste).toHaveLength(1)
  })
})

describe('fjernAeldre', () => {
  it('beholder punkter inden for levetiden og fjerner dem udenfor', () => {
    const liste = [peg(1, 0, 0, 0), peg(2, 0, 0, 900)]
    // Eksplicit levetid: punkt 1 er 1000 ms gammelt (ude), punkt 2 er 100 ms (inde).
    expect(fjernAeldre(liste, 1000, 1000)).toEqual([peg(2, 0, 0, 900)])
  })

  it('fjerner punktet naar levetiden er praecis naaet', () => {
    const liste = [peg(1, 0, 0, 0)]
    expect(fjernAeldre(liste, FADE_MS)).toEqual([])
  })
})

describe('opacitet', () => {
  it('er fuld ved alder 0 og nul ved levetidens udloeb', () => {
    expect(opacitet(0)).toBe(1)
    expect(opacitet(FADE_MS)).toBe(0)
    expect(opacitet(FADE_MS + 500)).toBe(0)
  })

  it('falder jaevn t i mellem', () => {
    expect(opacitet(FADE_MS / 2)).toBeCloseTo(0.5)
  })

  it('taaler negativ alder (ur der gaar tilbage) uden at give >1', () => {
    expect(opacitet(-50)).toBe(1)
  })
})

describe('sporStoerrelse', () => {
  it('vokser fra aeldste til nyeste', () => {
    expect(sporStoerrelse(0, 5)).toBeLessThan(sporStoerrelse(4, 5))
  })

  it('giver en brugbar stoerrelse for et enkelt punkt', () => {
    expect(sporStoerrelse(0, 1)).toBeGreaterThan(0)
  })
})
