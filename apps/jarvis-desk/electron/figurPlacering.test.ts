import { describe, expect, it } from 'vitest'
import { bobleSide, vindueTop } from './figurPlacering'

const skaerm = { x: 0, y: 0, width: 1920, height: 1080 }

describe('figurens plads paa skaermen', () => {
  it('viser boblen under figuren i øverste halvdel og over i nederste', () => {
    expect(bobleSide(180, skaerm)).toBe('under')
    expect(bobleSide(900, skaerm)).toBe('over')
  })

  it('holder figurens midte stationær ved vækst og retningsskift', () => {
    // Målt figurmidte 70 px fra indholdets top; indholdet er 180/275 px.
    const anker = 420
    const over = vindueTop(anker, 300, 275, 70, 'over')
    const under = vindueTop(anker, 300, 275, 70, 'under')
    expect(over).toBe(325)
    expect(under).toBe(350)
  })
})
