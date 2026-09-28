import { skalSpoergeOmVarsel } from './genoptagelsesVarsel'

/**
 * Reglen for HVORNÅR der spørges.
 *
 * Den er skrevet dyrt: i desk tog den fejl fire gange i træk, hver gang fordi
 * den lå flettet ind i en effekt hvor den kun kunne efterprøves ved at bygge
 * programmet og se efter. Testene her er de fire fejl, gjort til krav.
 */

const spoerg = (o: Partial<Parameters<typeof skalSpoergeOmVarsel>[0]> = {}) =>
  skalSpoergeOmVarsel({
    forrige: 'idle', status: 'idle', sessionId: 's1', alleredeSpurgt: null, ...o,
  })

describe('ved sessionsåbning', () => {
  it('spørger første gang en session er aktiv', () => {
    expect(spoerg().spoerg).toBe(true)
  })

  it('spørger IKKE igen for samme session', () => {
    expect(spoerg({ alleredeSpurgt: 's1' }).spoerg).toBe(false)
  })

  it('spørger igen når man skifter samtale', () => {
    expect(spoerg({ sessionId: 's2', alleredeSpurgt: 's1' }).spoerg).toBe(true)
  })

  it('uden en session spørges der ikke', () => {
    expect(spoerg({ sessionId: null }).spoerg).toBe(false)
  })
})

describe('når en tur slutter', () => {
  /** FEJL 1: `status === 'idle'` — men reduceren sætter `'done'`. */
  it.each(['done', 'interrupted', 'error'])(
    'ankomst i «%s» nulstiller, så der spørges igen', (status) => {
      const r = skalSpoergeOmVarsel({
        forrige: 'working', status, sessionId: 's1', alleredeSpurgt: 's1',
      })
      expect(r.nulstil).toBe(true)
      expect(r.spoerg).toBe(true)
    })

  /**
   * `hung` er mobilens egen, og den er MED med vilje: det er præcis den
   * tilstand hvor skærmen står stille og man tror turen er død. Er der et
   * varsel at hente, er det dér det skal siges.
   */
  it('«hung» tæller også — det er dér skærmen står stille', () => {
    const r = skalSpoergeOmVarsel({
      forrige: 'working', status: 'hung', sessionId: 's1', alleredeSpurgt: 's1',
    })
    expect(r.nulstil).toBe(true)
    expect(r.spoerg).toBe(true)
  })

  /** FEJL 3: mellemtilstanden «working» findes aldrig i en render. */
  it('kræver IKKE at forrige status var «working»', () => {
    const r = skalSpoergeOmVarsel({
      forrige: 'idle', status: 'done', sessionId: 's1', alleredeSpurgt: 's1',
    })
    expect(r.spoerg).toBe(true)
  })

  it('samme afsluttede status to gange i træk spørger kun én gang', () => {
    const r = skalSpoergeOmVarsel({
      forrige: 'done', status: 'done', sessionId: 's1', alleredeSpurgt: 's1',
    })
    expect(r.nulstil).toBe(false)
    expect(r.spoerg).toBe(false)
  })
})

describe('FEJL 4: der spørges uanset om noget kører', () => {
  /**
   * Effekten sprang før fra hvis der ikke kørte noget. Men et opgivet run fra
   * i går er netop det SSE aldrig kan fortælle om — og det er dét varslet
   * findes for.
   */
  it.each(['idle', 'working', 'done', 'hung'])(
    'status «%s» forhindrer ikke det første spørgsmål', (status) => {
      expect(spoerg({ status, forrige: status }).spoerg).toBe(true)
    })
})
