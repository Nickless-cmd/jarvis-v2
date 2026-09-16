import { describe, it, expect, beforeEach } from 'vitest'
import {
  klem, laesBredde, gemBredde, anvendBredde,
  MIN_BREDDE, MAKS_BREDDE, STANDARD_BREDDE, BREDDE_NOEGLE,
} from './sidebarBredde'

beforeEach(() => localStorage.clear())

describe('sidebarens bredde', () => {
  it('klemmer inden for grænserne', () => {
    expect(klem(50)).toBe(MIN_BREDDE)
    expect(klem(9999)).toBe(MAKS_BREDDE)
    expect(klem(300)).toBe(300)
  })

  it('en ugyldig værdi giver standarden — ikke 0', () => {
    // 0 ville skjule panelet uden at nogen havde bedt om det.
    expect(klem(NaN)).toBe(STANDARD_BREDDE)
    localStorage.setItem(BREDDE_NOEGLE, 'noget-vrøvl')
    expect(laesBredde()).toBe(STANDARD_BREDDE)
  })

  it('uden en gemt værdi bruges standarden', () => {
    expect(laesBredde()).toBe(STANDARD_BREDDE)
  })

  it('husker bredden — også klemt', () => {
    gemBredde(9999)
    expect(laesBredde()).toBe(MAKS_BREDDE)
  })

  it('skriver derhen hvor BEGGE læsere ser den', () => {
    // Gitteret og titelbjælken læser samme variabel på :root. En inline-bredde
    // på sidebaren ville lade bjælken blive stående og efterlade en stribe.
    anvendBredde(333)
    expect(document.documentElement.style.getPropertyValue('--sidebar-bredde')).toBe('333px')
  })

  it('anvendelse klemmer også', () => {
    anvendBredde(20)
    expect(document.documentElement.style.getPropertyValue('--sidebar-bredde')).toBe(`${MIN_BREDDE}px`)
  })
})
