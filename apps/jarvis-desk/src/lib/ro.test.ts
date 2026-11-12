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

// ── Opdagelse af et NYT run må ikke bremses af hvile-tilstanden (12/11-2026) ───
//
// Målt på CT105: wake-runnet autonomous-7d13b933 startede 19:11:20 og varede 20 s,
// men desk tilsluttede sig først 19:11:37 — 3 s før det sluttede, og med alle 305
// frames på én gang («kastet ind»). /chat/active-runs blev spurgt 19:10:49, :10:59,
// :11:13 og så :11:37: et hul på 24 s hen over runnets start. Han sad og ventede på
// vækningen uden at røre skærmen, altså netop «ro» (3 min uden input → faktor 8), og
// hvile-faktoren ramte både pollen OG den delte cache. Hvile skal spare en SOVENDE
// eller SKJULT skærm — ikke en der kigges på.
describe('loftSynligMs — et synligt vindue opdager nyt arbejde hurtigt, selv i ro', () => {
  const valg = { loftSynligMs: 2000 }

  it('i ro og SYNLIGT slippes der igennem hvert loft, ikke hvert forlænget interval', () => {
    gaa(ROLIG_EFTER_MS + 1)
    expect(maaPolle('aktive-runs', 1500, valg)).toBe(true)
    gaa(1500)
    expect(maaPolle('aktive-runs', 1500, valg)).toBe(false)   // 1,5 s < loftet 2 s
    gaa(600)
    expect(maaPolle('aktive-runs', 1500, valg)).toBe(true)    // 2,1 s ≥ 2 s (uden loft: 12 s)
  })

  it('uden loftSynligMs er adfærden UÆNDRET: 12 s i ro', () => {
    gaa(ROLIG_EFTER_MS + 1)
    expect(maaPolle('t', 1500)).toBe(true)
    gaa(5000)
    expect(maaPolle('t', 1500)).toBe(false)
    gaa(7001)
    expect(maaPolle('t', 1500)).toBe(true)
  })

  it('et SKJULT vindue holder fortsat sin langsomme takt — loftet gælder kun synlige', () => {
    vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('hidden')
    gaa(ROLIG_EFTER_MS + 1)
    expect(maaPolle('aktive-runs', 1500, valg)).toBe(true)
    gaa(10_000)
    expect(maaPolle('aktive-runs', 1500, valg)).toBe(false)   // 1,5 s × 20 = 30 s
    gaa(20_001)
    expect(maaPolle('aktive-runs', 1500, valg)).toBe(true)
  })

  it('loftet gør aldrig intervallet LÆNGERE end det var', () => {
    gaa(ROLIG_EFTER_MS + 1)
    expect(maaPolle('hurtig', 500, { loftSynligMs: 2000 })).toBe(true)
    gaa(400)
    expect(maaPolle('hurtig', 500, { loftSynligMs: 2000 })).toBe(false)   // 500 × 8 = 4 s → loft 2 s
    gaa(1700)
    expect(maaPolle('hurtig', 500, { loftSynligMs: 2000 })).toBe(true)
  })
})
