import { describe, it, expect, vi, afterEach } from 'vitest'
import { laesKrav, boerFornys, fornyOmNoedvendigt, type ApiConfig } from './tokenRenewal'

/**
 * Mikkels telefon gav 927 × 401 på seks timer med `token expired` og havde
 * ingen vej tilbage. Desk har samme sygdom — bare langsommere, fordi Bjørn
 * selv kan geninstallere sit token. Det disse tests holder på, er de tre ting der gør
 * fornyelsen brugbar: den ved HVORNÅR, den kan læse et token uden hjælp fra
 * runtimen, og den vælter aldrig opstarten.
 */

function jwt(iat: number, exp: number): string {
  const b64 = (o: unknown) =>
    btoa(JSON.stringify(o))
      .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '')
  return `${b64({ alg: 'HS256' })}.${b64({ sub: 'u', iat, exp })}.signatur`
}

const NU = 1_770_000_000_000          // ms
const S = NU / 1000                   // sekunder
// Et token der ER udløbet — præcis Mikkels tilstand.
const cfg: ApiConfig = { apiBaseUrl: 'http://x/', authToken: jwt(S - 400 * 86400, S - 5 * 86400) }

describe('at læse tokenet', () => {
  it('læser iat/exp uden atob', () => {
    // Egen afkoder med vilje: `atob` findes ikke pålideligt i alle RN-runtimes,
    // og en fornyelse der stille kaster på nogle telefoner er værre end ingen.
    expect(laesKrav(jwt(100, 200))).toEqual({ iat: 100, exp: 200 })
  })

  it('giver null på noget der ikke er et JWT', () => {
    expect(laesKrav('ikke-et-token')).toBeNull()
    expect(laesKrav('')).toBeNull()
  })
})

describe('hvornår der fornys', () => {
  it('ikke mens der er rigeligt tilbage', () => {
    expect(boerFornys(jwt(S - 10 * 86400, S + 355 * 86400), NU)).toBe(false)
  })

  it('når under en tredjedel er tilbage', () => {
    // Pointen: vi venter IKKE på en 401. Et token der udløber mens telefonen
    // ligger i en skuffe fejler ikke — det bliver bare gammelt.
    expect(boerFornys(jwt(S - 300 * 86400, S + 65 * 86400), NU)).toBe(true)
  })

  it('når det allerede er udløbet', () => {
    expect(boerFornys(jwt(S - 400 * 86400, S - 5 * 86400), NU)).toBe(true)
  })

  it('når vi ikke kan læse det — så lad serveren dømme', () => {
    expect(boerFornys('vrøvl', NU)).toBe(true)
  })
})

describe('selve fornyelsen', () => {
  const friskt = jwt(S, S + 365 * 86400)

  afterEach(() => { (global as any).fetch = undefined })

  it('gemmer det nye token og bruger det', async () => {
    const gem = vi.fn().mockResolvedValue(undefined)
    ;(global as any).fetch = vi.fn().mockResolvedValue({
      ok: true, json: async () => ({ token: friskt })
    })

    const ud = await fornyOmNoedvendigt(cfg, gem, NU)

    expect(ud.authToken).toBe(friskt)
    expect(gem).toHaveBeenCalledWith(expect.objectContaining({ authToken: friskt }))
    expect((global as any).fetch).toHaveBeenCalledWith(
      'http://x/api/auth/renew',
      expect.objectContaining({ method: 'POST' })
    )
  })

  it('sender det NUVÆRENDE token med — også det udløbne', async () => {
    // Serveren veksler netop det udløbne token. Sender vi intet, er der intet
    // at forny fra.
    const kaldt: any[] = []
    ;(global as any).fetch = vi.fn(async (_u: string, o: any) => {
      kaldt.push(o.headers.Authorization)
      return { ok: true, json: async () => ({ token: friskt }) }
    })
    await fornyOmNoedvendigt(cfg, vi.fn(), NU)
    expect(kaldt[0]).toBe(`Bearer ${cfg.authToken}`)
  })

  it('rører ikke serveren når tokenet er friskt', async () => {
    ;(global as any).fetch = vi.fn()
    const ud = await fornyOmNoedvendigt({ ...cfg, authToken: friskt }, vi.fn(), NU)
    expect(ud.authToken).toBe(friskt)
    expect((global as any).fetch).not.toHaveBeenCalled()
  })

  it('beholder det gamle token når serveren siger nej', async () => {
    ;(global as any).fetch = vi.fn().mockResolvedValue({ ok: false, json: async () => ({}) })
    expect((await fornyOmNoedvendigt(cfg, vi.fn(), NU)).authToken).toBe(cfg.authToken)
  })

  it('vælter ikke opstarten når der ikke er net', async () => {
    // En telefon uden net skal starte på det token den har. Nådevinduet på
    // serveren er der netop for at det må tage tid.
    ;(global as any).fetch = vi.fn().mockRejectedValue(new Error('ingen net'))
    const gem = vi.fn()
    await expect(fornyOmNoedvendigt(cfg, gem, NU)).resolves.toEqual(cfg)
    expect(gem).not.toHaveBeenCalled()
  })

  it('gemmer ikke et tomt token', async () => {
    ;(global as any).fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => ({ token: '' }) })
    const gem = vi.fn()
    expect((await fornyOmNoedvendigt(cfg, gem, NU)).authToken).toBe(cfg.authToken)
    expect(gem).not.toHaveBeenCalled()
  })
})
