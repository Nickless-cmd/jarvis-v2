jest.mock('./broOpstart', () => ({ klientId: jest.fn(async () => 'mobil-1') }))
jest.mock('./telefonHandlere', () => ({
  KAN_UDFOERE: ['phone_location'],
  udfoerVaerktoej: jest.fn(async () => ({}))
}))

import {
  erVaekning, haandterVaekning, TOMGANG_MS, LOFT_MS, VAEKNING_KIND
} from './broVaekning'

const CONFIG = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'test-token' } // noqa: literal-credential

/** Styret ur, så vinduerne kan afprøves uden at vente i rigtig tid. */
function ur() {
  let t = 0
  return {
    naa: () => t,
    vent: async (ms: number) => { t += ms },
    spol: (ms: number) => { t += ms }
  }
}

describe('genkendelse', () => {
  it('kender vækningen på dens kind', () => {
    expect(erVaekning({ kind: VAEKNING_KIND })).toBe(true)
    expect(erVaekning({ kind: 'reminder' })).toBe(false)
    expect(erVaekning(null)).toBe(false)
    expect(erVaekning({})).toBe(false)
  })
})

describe('vinduet', () => {
  it('lukker broen når der ikke sker noget', async () => {
    const u = ur()
    const stop = jest.fn()
    const r = await haandterVaekning(CONFIG, {
      naa: u.naa, vent: u.vent,
      lavBro: () => ({ start: jest.fn(), stop, erForbundet: () => true, forsoeg: () => 0 })
    })
    expect(stop).toHaveBeenCalled()
    expect(r.kald).toBe(0)
    expect(u.naa()).toBeGreaterThanOrEqual(TOMGANG_MS)
  })

  it('forlænges når der faktisk kommer kald', async () => {
    // Kommer der ét kald, er der sandsynligvis flere i samme tur — og det
    // ville være dumt at lukke midt i en runde.
    const u = ur()
    let paaAktivitet = () => {}
    const start = jest.fn(() => {
      // to kald med god afstand, som ville have ligget efter tomgangsgrænsen
      setTimeout(() => paaAktivitet(), 0)
    })
    const p = haandterVaekning(CONFIG, {
      naa: u.naa, vent: u.vent,
      lavBro: (_c, _id, paa) => {
        paaAktivitet = paa
        return { start, stop: jest.fn(), erForbundet: () => true, forsoeg: () => 0 }
      }
    })
    // lad broen "modtage" kald undervejs
    for (let i = 0; i < 3; i++) {
      await Promise.resolve()
      paaAktivitet()
    }
    const r = await p
    expect(r.kald).toBeGreaterThan(0)
  })

  it('holder op ved loftet selv med kald på kald', async () => {
    // En vækning må ikke blive til en permanent forbindelse — dét er en
    // foreground-service, og det er en anden beslutning med et ikon Bjørn
    // skal sige ja til.
    const u = ur()
    let paaAktivitet = () => {}
    const stop = jest.fn()
    const p = haandterVaekning(CONFIG, {
      naa: u.naa,
      vent: async (ms) => { u.spol(ms); paaAktivitet() },  // aktivitet HVER runde
      lavBro: (_c, _id, paa) => {
        paaAktivitet = paa
        return { start: jest.fn(), stop, erForbundet: () => true, forsoeg: () => 0 }
      }
    })
    await p
    expect(stop).toHaveBeenCalled()
    expect(u.naa()).toBeGreaterThanOrEqual(LOFT_MS)
    expect(u.naa()).toBeLessThan(LOFT_MS + 2000)
  })

  it('lukker broen også når noget kaster undervejs', async () => {
    const stop = jest.fn()
    await expect(haandterVaekning(CONFIG, {
      naa: () => 0,
      vent: async () => { throw new Error('afbrudt') },
      lavBro: () => ({ start: jest.fn(), stop, erForbundet: () => true, forsoeg: () => 0 })
    })).rejects.toThrow('afbrudt')
    expect(stop).toHaveBeenCalled()
  })
})
