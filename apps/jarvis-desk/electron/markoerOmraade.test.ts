import { describe, expect, it } from 'vitest'
import { unionAf, type Skærm } from './markoerOmraade'

/** Bjørns faktiske opsætning, målt 21/9-2026 med xrandr + xdpyinfo. */
const BJOERNS_TRE: Skærm[] = [
  { x: 0, y: 0, width: 1920, height: 1080 },    // head #2 (DP-4)
  { x: 1920, y: 0, width: 1920, height: 1080 }, // head #0 (DP-0)
  { x: 3840, y: 0, width: 1920, height: 1080 }, // head #1 (DP-2)
]

describe('unionAf', () => {
  it('giver hele skrivebordet for Bjoerns tre skaerme', () => {
    expect(unionAf(BJOERNS_TRE)).toEqual({ x: 0, y: 0, width: 5760, height: 1080 })
  })

  it('haandterer en enkelt skaerm', () => {
    expect(unionAf([{ x: 0, y: 0, width: 1920, height: 1080 }]))
      .toEqual({ x: 0, y: 0, width: 1920, height: 1080 })
  })

  it('bevarer negativ x naar en skaerm staar til venstre for den primaere', () => {
    // X11 giver den venstre skaerm negative koordinater. Klippede man til nul,
    // ville laget ligge forskudt paa praecis de opsaetninger.
    const s = unionAf([
      { x: -1920, y: 0, width: 1920, height: 1080 },
      { x: 0, y: 0, width: 1920, height: 1080 },
    ])
    expect(s).toEqual({ x: -1920, y: 0, width: 3840, height: 1080 })
  })

  it('regner hoejden ud af skaer men forskellig hoejde', () => {
    const s = unionAf([
      { x: 0, y: 0, width: 1920, height: 1080 },
      { x: 1920, y: -200, width: 1080, height: 1920 },
    ])
    expect(s).toEqual({ x: 0, y: -200, width: 3000, height: 1920 })
  })

  it('taaler en tom liste uden at kaste (Math.min af tom = Infinity)', () => {
    expect(unionAf([])).toEqual({ x: 0, y: 0, width: 0, height: 0 })
  })
})
