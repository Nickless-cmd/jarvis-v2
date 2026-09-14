import { boerSpoerge, hentForslag, saetSammen, MIN_TEGN } from './forslag'

/**
 * Forslag i komponisten. Reglerne herunder findes ogsaa paa serveren — og det
 * er med vilje: hvert tastetryk der ikke bliver til et kald, er GPU der ikke
 * konkurrerer med det synlige svar. Huset har den erfaring skrevet ned
 * (recall-embeds koeede 28-91 sekunder bag et svar paa samme ollama).
 */

describe('boerSpoerge', () => {
  it('siger nej til et for kort udkast', () => {
    expect(boerSpoerge('ka')).toBe(false)
    expect(boerSpoerge('')).toBe(false)
    expect(boerSpoerge('   ')).toBe(false)
  })

  it('siger ja naar der er noget at gaette paa', () => {
    expect(boerSpoerge('kan du lige tjekke')).toBe(true)
  })

  it('siger nej til en FAERDIG saetning', () => {
    // At foreslaa videre dér er at tale i munden paa ham.
    expect(boerSpoerge('kan du tjekke det?')).toBe(false)
    expect(boerSpoerge('gør det.')).toBe(false)
    expect(boerSpoerge('ja, kør!')).toBe(false)
  })

  it('siger nej til et helt afsnit', () => {
    expect(boerSpoerge('x '.repeat(400))).toBe(false)
  })

  it('bruger SAMME graense som serveren', () => {
    // Var de forskellige, ville klienten enten spoerge forgaeves eller tie
    // hvor serveren gerne ville svare.
    expect(MIN_TEGN).toBe(8)
  })
})

describe('saetSammen', () => {
  it('haefter forslaget paa', () => {
    expect(saetSammen('kan du lige', ' tjekke det')).toBe('kan du lige tjekke det')
  })

  it('laver ikke to mellemrum', () => {
    // Serveren haefter allerede et mellemrum paa fortsaettelsen. Skriver man
    // selv et til sidst, ville to blive til «tjekke  det».
    expect(saetSammen('kan du lige ', ' tjekke det')).toBe('kan du lige tjekke det')
  })

  it('et tomt forslag aendrer intet', () => {
    expect(saetSammen('kan du lige', '')).toBe('kan du lige')
  })

  it('tegnsaetning haefter uden mellemrum', () => {
    expect(saetSammen('kan du tjekke det', ', tak')).toBe('kan du tjekke det, tak')
  })
})

describe('hentForslag', () => {
  const svar = (body: unknown, ok = true) =>
    Promise.resolve({ ok, json: () => Promise.resolve(body) } as Response)

  afterEach(() => {
    // @ts-expect-error — testens egen opsaetning
    global.fetch = undefined
  })

  it('henter forslaget', async () => {
    global.fetch = jest.fn(() => svar({ forslag: ' tjekke det' })) as unknown as typeof fetch
    expect(await hentForslag('http://x', 't', 'kan du lige tjekke')).toBe(' tjekke det')
  })

  it('spoerger SLET IKKE naar udkastet ikke indbyder til det', async () => {
    const f = jest.fn(() => svar({ forslag: 'x' }))
    global.fetch = f as unknown as typeof fetch
    expect(await hentForslag('http://x', 't', 'ka')).toBe('')
    expect(f).not.toHaveBeenCalled()
  })

  it('giver tomt ved en fejlkode', async () => {
    global.fetch = jest.fn(() => svar({ forslag: 'x' }, false)) as unknown as typeof fetch
    expect(await hentForslag('http://x', 't', 'kan du lige tjekke')).toBe('')
  })

  it('giver tomt naar netvaerket fejler — komponisten skal kunne skrives i', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('nede'))) as unknown as typeof fetch
    expect(await hentForslag('http://x', 't', 'kan du lige tjekke')).toBe('')
  })

  it('giver tomt naar svaret ikke er en streng', async () => {
    global.fetch = jest.fn(() => svar({ forslag: 42 })) as unknown as typeof fetch
    expect(await hentForslag('http://x', 't', 'kan du lige tjekke')).toBe('')
  })

  it('sender udkastet med — og tokenet', async () => {
    const f = jest.fn(() => svar({ forslag: '' }))
    global.fetch = f as unknown as typeof fetch
    await hentForslag('http://x', 'hemmelig', 'kan du lige tjekke')
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://x/composer/suggest')
    expect(JSON.parse(String(init.body))).toEqual({ udkast: 'kan du lige tjekke' })
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer hemmelig')
  })

  it('kan afbrydes naar brugeren skriver videre', async () => {
    // Uden det ville et langsomt svar kunne lande ovenpaa et nyere og foreslaa
    // noget der passede til en saetning der ikke findes mere.
    const f = jest.fn(() => svar({ forslag: '' }))
    global.fetch = f as unknown as typeof fetch
    const c = new AbortController()
    await hentForslag('http://x', 't', 'kan du lige tjekke', c.signal)
    const [, init] = f.mock.calls[0] as unknown as [string, RequestInit]
    expect(init.signal).toBe(c.signal)
  })
})
