import { hentNaesteForslag, meldValg, INTET_FORSLAG, HENT_PAUSE_MS } from './forslag'

/**
 * Forslag i komponisten — den NÆSTE besked, ikke en fortsættelse.
 *
 * Formen er nu den samme som desk: ét forslag, hentet når feltet er TOMT, med
 * sessionen med så serveren kan give Jarvis' eget forslag videre. Den gamle
 * fortsættelses-form — send hans halvskrevne udkast og få resten af sætningen
 * — er væk. Bjørn 24/9-2026: «lige nu er det en model der gætter på mine
 * næste ord udfra det jeg skriver, det er lidt mærkeligt».
 */

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

const svar = (body: unknown, ok = true) =>
  Promise.resolve({ ok, json: () => Promise.resolve(body) } as Response)

afterEach(() => {
  // @ts-expect-error — testens egen opsætning
  global.fetch = undefined
})

describe('hentNaesteForslag', () => {
  it('henter forslaget med id og kilde', async () => {
    global.fetch = jest.fn(() =>
      svar({ forslag: 'Skal vi teste den?', forslag_id: 'cj-1', kilde_besked_id: 'm-1' })
    ) as unknown as typeof fetch
    expect(await hentNaesteForslag(cfg, 's1')).toEqual({
      tekst: 'Skal vi teste den?',
      id: 'cj-1',
      kildeBeskedId: 'm-1',
    })
  })

  it('sender TOMT udkast og sessionen med', async () => {
    // Det er hele forskellen fra den gamle form: udkastet er tomt, så serveren
    // bygger på SAMTALEN — og sessionen er dét der lader Jarvis' eget forslag
    // ligge klar til at blive hentet i stedet for den lokale models gæt.
    const f = jest.fn(() => svar({ forslag: '' }))
    global.fetch = f as unknown as typeof fetch
    await hentNaesteForslag(cfg, 's1')
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://x/composer/suggest')
    expect(JSON.parse(String(init.body))).toEqual({ udkast: '', session_id: 's1' })
    expect((init.headers as Record<string, string>).Authorization).toBe('Bearer t')
  })

  it('spoerger SLET IKKE uden en session', async () => {
    const f = jest.fn(() => svar({ forslag: 'x' }))
    global.fetch = f as unknown as typeof fetch
    expect(await hentNaesteForslag(cfg, '')).toEqual(INTET_FORSLAG)
    expect(f).not.toHaveBeenCalled()
  })

  it('giver tomt ved en fejlkode', async () => {
    global.fetch = jest.fn(() => svar({ forslag: 'x' }, false)) as unknown as typeof fetch
    expect(await hentNaesteForslag(cfg, 's1')).toEqual(INTET_FORSLAG)
  })

  it('giver tomt naar netvaerket fejler — komponisten skal kunne skrives i', async () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('nede'))) as unknown as typeof fetch
    expect(await hentNaesteForslag(cfg, 's1')).toEqual(INTET_FORSLAG)
  })

  it('giver tomt naar forslaget ikke er en streng', async () => {
    global.fetch = jest.fn(() => svar({ forslag: 42 })) as unknown as typeof fetch
    expect(await hentNaesteForslag(cfg, 's1')).toEqual(INTET_FORSLAG)
  })

  it('kan afbrydes naar han skriver videre', async () => {
    // Uden det ville et langsomt svar kunne lande ovenpaa et nyere og foreslaa
    // noget der hørte til en samtale der er kørt videre.
    const f = jest.fn(() => svar({ forslag: '' }))
    global.fetch = f as unknown as typeof fetch
    const c = new AbortController()
    await hentNaesteForslag(cfg, 's1', c.signal)
    const [, init] = f.mock.calls[0] as unknown as [string, RequestInit]
    expect(init.signal).toBe(c.signal)
  })
})

describe('meldValg', () => {
  it('sender valget — og ALDRIG hans egen tekst', async () => {
    // Kun ét bit om at forslaget ikke blev brugt. Det eneste tekstlige i
    // kaldet er forslagets EGNE ord, som serveren selv har fundet på.
    const f = jest.fn(() => svar({ ok: true }))
    global.fetch = f as unknown as typeof fetch
    meldValg(cfg, { tekst: 'Skal vi teste?', id: 'cj-1', kildeBeskedId: 'm-1' }, 'eget', 's1')
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit]
    expect(url).toBe('http://x/composer/choice')
    expect(JSON.parse(String(init.body))).toEqual({
      forslag_id: 'cj-1',
      session_id: 's1',
      forslag: 'Skal vi teste?',
      kilde_besked_id: 'm-1',
      valg: 'eget',
    })
  })

  it('melder intet uden et forslags-id', () => {
    const f = jest.fn()
    global.fetch = f as unknown as typeof fetch
    meldValg(cfg, INTET_FORSLAG, 'vist', 's1')
    expect(f).not.toHaveBeenCalled()
  })

  it('kaster ikke naar netvaerket er nede', () => {
    global.fetch = jest.fn(() => Promise.reject(new Error('nede'))) as unknown as typeof fetch
    expect(() =>
      meldValg(cfg, { tekst: 'x', id: 'cj-1', kildeBeskedId: '' }, 'vist', 's1')
    ).not.toThrow()
  })
})

describe('HENT_PAUSE_MS', () => {
  it('er samme pause som desk', () => {
    expect(HENT_PAUSE_MS).toBe(700)
  })
})
