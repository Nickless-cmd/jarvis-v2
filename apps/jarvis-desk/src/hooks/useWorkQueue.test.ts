import { describe, expect, it } from 'vitest'
import { spandForRun } from '../lib/coworkApi'

/** Spandene er valgt efter hvad man kan GØRE ved tingene. */
describe('spandForRun', () => {
  it('kørende hører til Kører nu', () => {
    for (const s of ['running', 'active', 'streaming', 'RUNNING']) {
      expect(spandForRun(s)).toBe('aktiv')
    }
  })

  it('fejl og annullering hører til Fejlet', () => {
    for (const s of ['failed', 'cancelled', 'error']) {
      expect(spandForRun(s)).toBe('fejlet')
    }
  })

  it('afbrudt er hverken fejlet eller færdigt — det fortjener et blik', () => {
    // En afbrudt tur efterlod noget halvt. At kalde den «fejlet» ville
    // skjule at der måske ligger brugbart arbejde; «færdig» ville lyve.
    expect(spandForRun('interrupted')).toBe('til_gennemsyn')
  })

  it('resten er historik', () => {
    expect(spandForRun('completed')).toBe('faerdig')
    expect(spandForRun('')).toBe('faerdig')
  })
})
