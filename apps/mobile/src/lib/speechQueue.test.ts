import { hasOpenFence, takeSpeakable } from './speechQueue'

describe('takeSpeakable', () => {
  it('afleverer en færdig sætning og husker hvor langt den nåede', () => {
    const full = 'Jeg har kigget på containeren i nat. Alt kø'
    const r = takeSpeakable(full, 0)
    expect(r.chunks).toEqual(['Jeg har kigget på containeren i nat.'])
    // Halvdelen af næste sætning må IKKE med — den er ikke færdig endnu.
    expect(full.slice(r.taken)).toBe(' Alt kø')
  })

  it('siger ikke det samme to gange når mere tekst kommer til', () => {
    const a = takeSpeakable('Første sætning står færdig her. Anden', 0)
    const b = takeSpeakable('Første sætning står færdig her. Anden sætning er også færdig nu.', a.taken)
    expect(a.chunks).toEqual(['Første sætning står færdig her.'])
    expect(b.chunks).toEqual(['Anden sætning er også færdig nu.'])
  })

  // «Ja.» alene ville blive sagt, og så en pause, og så resten. Det lyder
  // afhakket — korte stumper hører sammen med det der følger.
  it('slår en kort stump sammen med den næste sætning', () => {
    const r = takeSpeakable('Ja. Det har jeg allerede kigget grundigt på.', 0)
    expect(r.chunks).toEqual(['Ja. Det har jeg allerede kigget grundigt på.'])
  })

  it('holder en uafsluttet kodeblok tilbage', () => {
    const full = 'Kør denne kommando nu med det samme. ```bash\nls -la'
    expect(takeSpeakable(full, 0).chunks).toEqual([])
  })

  it('slipper kodeblokken igennem når den er lukket', () => {
    const full = 'Kør denne kommando nu med det samme. ```bash\nls -la\n``` Så er du klar.'
    expect(takeSpeakable(full, 0).chunks.join(' ')).toContain('Kør denne kommando')
  })

  // Uden dette ville en lang stribe uden tegnsætning aldrig blive sagt.
  it('bryder ved et mellemrum når der ingen tegnsætning er', () => {
    const full = 'ord '.repeat(90)
    const r = takeSpeakable(full, 0)
    expect(r.chunks).toHaveLength(1)
    const only = r.chunks[0] as string
    expect(only.length).toBeLessThanOrEqual(260)
    expect(only.endsWith('ord')).toBe(true)
  })

  it('tager resten med når svaret er færdigt', () => {
    const full = 'Den første sætning står helt færdig her. Halv sætning uden punktum'
    const r = takeSpeakable(full, 0, true)
    expect(r.chunks).toEqual(['Den første sætning står helt færdig her.', 'Halv sætning uden punktum'])
    expect(r.taken).toBe(full.length)
  })

  it('deler ikke midt i et decimaltal eller en forkortelse', () => {
    const r = takeSpeakable('Disken er 3.4 TB stor og bl.a. næsten fuld nu.', 0)
    expect(r.chunks).toEqual(['Disken er 3.4 TB stor og bl.a. næsten fuld nu.'])
  })

  it('siger ingenting når der intet nyt er', () => {
    expect(takeSpeakable('Hele svaret er sagt.', 20).chunks).toEqual([])
  })

  it('kender en åben kodeblok fra en lukket', () => {
    expect(hasOpenFence('```bash\nls')).toBe(true)
    expect(hasOpenFence('```bash\nls\n```')).toBe(false)
  })
})
