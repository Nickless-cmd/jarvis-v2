import { describe, it, expect, beforeEach } from 'vitest'
import {
  anvendBredde, gemBredde, klem, laesBredde, BREDDE_NOEGLE,
  MAKS_BREDDE, MIN_BREDDE, STANDARD_BREDDE,
} from './skinneBredde'

describe('skinneBredde', () => {
  beforeEach(() => {
    localStorage.clear()
    document.documentElement.style.removeProperty('--skinne-bredde')
  })

  it('klemmer til graenserne', () => {
    expect(klem(10)).toBe(MIN_BREDDE)
    expect(klem(99999)).toBe(MAKS_BREDDE)
    expect(klem(420)).toBe(420)
  })

  it('en ugyldig vaerdi giver standarden — ikke 0, som ville SKJULE skinnen', () => {
    expect(klem(Number.NaN)).toBe(STANDARD_BREDDE)
    expect(klem(0)).toBe(MIN_BREDDE)
  })

  it('laeser og gemmer', () => {
    expect(laesBredde()).toBe(STANDARD_BREDDE)
    gemBredde(500)
    expect(laesBredde()).toBe(500)
    expect(localStorage.getItem(BREDDE_NOEGLE)).toBe('500')
  })

  it('en gemt vaerdi uden for graenserne klemmes ved laesning', () => {
    // Uden dette ville et gammelt tal kunne aabne appen med en skinne der
    // daekker hele skaermen.
    localStorage.setItem(BREDDE_NOEGLE, '9999')
    expect(laesBredde()).toBe(MAKS_BREDDE)
  })

  it('anvendBredde skriver CSS-variablen — den BAADE skinnen og paddingen laeser', () => {
    // Skinnen har width: var(--skinne-bredde); samtalen goer plads med
    // padding-right: calc(var(--skinne-bredde) + 16px). Skrives bredden et
    // andet sted end stylesheet'et, bliver paddingen staaende og efterlader
    // en stribe tomt.
    anvendBredde(400)
    expect(document.documentElement.style.getPropertyValue('--skinne-bredde')).toBe('400px')
  })
})
