import { noterEvent, hentOgRyd, _nulstil } from './streamTempo'

// Uret styres, saa tallet ikke afhaenger af maskinen testen koerer paa.
let nu = 0
const ægteNow = Date.now
beforeEach(() => { _nulstil(); nu = 1_000_000; Date.now = () => nu })
afterEach(() => { Date.now = ægteNow })

const ankomst = (gaps: number[], run = 'r1') => {
  noterEvent(run)
  for (const g of gaps) { nu += g; noterEvent(run) }
}

describe('streamTempo', () => {
  it('under 20 events giver intet tal — for lidt til at konkludere', () => {
    ankomst([10, 10, 10])
    expect(hentOgRyd()).toBeNull()
  })

  it('JAEVN ankomst: lav andel under 2 ms', () => {
    // Serveren leverede median 110 tok/s 1/10 — altsaa ~9 ms mellem deltaer.
    ankomst(Array.from({ length: 40 }, () => 9))
    const u = hentOgRyd()!
    expect(u.median_ms).toBe(9)
    expect(u.andel_under_2ms).toBe(0)
  })

  it('KLUMPET ankomst: hoej andel under 2 ms OG stor maks', () => {
    // Det native lag giver JS en bunke ad gangen: fem naer-nul, saa en pause.
    const gaps: number[] = []
    for (let i = 0; i < 10; i++) gaps.push(120, 0, 0, 0, 0)
    ankomst(gaps)
    const u = hentOgRyd()!
    expect(u.andel_under_2ms).toBeGreaterThan(70)
    expect(u.maks_ms).toBe(120)
    // Medianen alene ville sige «0 ms, helt jaevnt» — derfor maaler vi begge.
    expect(u.median_ms).toBe(0)
  })

  it('et nyt run begynder forfra', () => {
    ankomst(Array.from({ length: 30 }, () => 5), 'r1')
    noterEvent('r2')
    ankomst(Array.from({ length: 3 }, () => 5), 'r2')
    expect(hentOgRyd()).toBeNull()   // kun faa events i r2
  })

  it('hentOgRyd rydder, saa naeste ping ikke sender det samme igen', () => {
    ankomst(Array.from({ length: 40 }, () => 9))
    expect(hentOgRyd()).not.toBeNull()
    expect(hentOgRyd()).toBeNull()
  })
})
