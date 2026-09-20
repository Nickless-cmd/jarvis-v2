/**
 * Ro-tilstand. Målt 20/9-2026 kl. 03-04 på CT105: 31.146 kald i én time mens
 * Bjørn sov, 23.070 af dem fra én desk. Det farlige ved en bremse er ikke at
 * den bremser for lidt — det er at den bremser live-arbejde eller lader en
 * skærm stå forældet når han kommer tilbage. Begge dele står pinnet nedenfor.
 */
import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import {
  FAKTOR_RO, FAKTOR_SKJULT, LOFT_MS, ROLIG_EFTER_MS,
  _nulstil, _saetUr, maaPolle, roFaktor, vaagn,
} from './ro'

let nu = 1_000_000

beforeEach(() => {
  nu = 1_000_000
  _saetUr(() => nu)
  _nulstil()
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
})

afterEach(() => {
  vi.restoreAllMocks()
  _saetUr(() => Date.now())
})

const gaa = (ms: number) => { nu += ms }

describe('faktoren', () => {
  it('er 1 mens nogen er i gang', () => {
    expect(roFaktor()).toBe(1)
  })

  it('stiger efter tre minutter uden et tegn på liv', () => {
    gaa(ROLIG_EFTER_MS + 1)
    expect(roFaktor()).toBe(FAKTOR_RO)
  })

  it('er højest når vinduet er skjult', () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    expect(roFaktor()).toBe(FAKTOR_SKJULT)
  })

  it('er ALTID 1 mens noget streamer — også ved et skjult vindue', () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    gaa(ROLIG_EFTER_MS * 10)
    expect(roFaktor({ fuldFart: true })).toBe(1)
  })

  it('ignorerSkjult: et minimeret vindue tæller som roligt, ikke som væk', () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    expect(roFaktor({ ignorerSkjult: true })).toBe(1)
    gaa(ROLIG_EFTER_MS + 1)
    expect(roFaktor({ ignorerSkjult: true })).toBe(FAKTOR_RO)
  })
})

describe('maaPolle', () => {
  it('slipper ALT igennem mens nogen arbejder', () => {
    for (let i = 0; i < 10; i++) {
      expect(maaPolle('t', 1500)).toBe(true)
      gaa(1500)
    }
  })

  it('springer tick over i ro, men lader ét igennem pr. forlænget interval', () => {
    gaa(ROLIG_EFTER_MS + 1)
    expect(maaPolle('t', 1500)).toBe(true)          // første i ro
    let sluppet = 0
    for (let i = 0; i < 20; i++) {                   // 20 tick à 1,5 s = 30 s
      gaa(1500)
      if (maaPolle('t', 1500)) sluppet += 1
    }
    // 1500 × 8 = 12 s → 30 s rummer to.
    expect(sluppet).toBe(2)
  })

  it('loftet holder: et langsomt interval bliver ikke uendeligt', () => {
    gaa(ROLIG_EFTER_MS + 1)
    maaPolle('jobs', 15_000)
    gaa(LOFT_MS + 1)
    expect(maaPolle('jobs', 15_000)).toBe(true)      // 15 s × 8 = 120 s, loft 60 s
  })

  it('EGET loft respekteres — notifikationer må ikke vente et minut', () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    gaa(ROLIG_EFTER_MS + 1)
    const valg = { ignorerSkjult: true, loftMs: 15_000 }
    maaPolle('notifikationer', 3000, valg)
    gaa(15_001)
    expect(maaPolle('notifikationer', 3000, valg)).toBe(true)
  })

  it('et tegn på liv gør skærmen frisk MED DET SAMME', () => {
    gaa(ROLIG_EFTER_MS + 1)
    maaPolle('t', 1500)
    gaa(1500)
    expect(maaPolle('t', 1500)).toBe(false)          // stadig i ro
    vaagn()                                           // han rører musen
    expect(maaPolle('t', 1500)).toBe(true)           // næste tick henter straks
  })

  it('nøglerne holdes adskilt', () => {
    gaa(ROLIG_EFTER_MS + 1)
    expect(maaPolle('a', 1500)).toBe(true)
    expect(maaPolle('b', 1500)).toBe(true)
    expect(maaPolle('a', 1500)).toBe(false)
  })
})
