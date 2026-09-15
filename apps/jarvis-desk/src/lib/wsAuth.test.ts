import { describe, it, expect, vi, afterEach } from 'vitest'
import { openEventSocket, WS_SUBPROTOKOL } from './api'

/**
 * `/ws` streamede hele event-bussen UDEN auth indtil 15/9-2026 — indre stemme,
 * ræsonnements-konklusioner, private_brain — til enhver der forbandt.
 *
 * Denne test findes fordi mutationen «hjælperen dropper tokenet» overlevede en
 * kildevagt. Og netop den fejl er tavs: socketen falder tilbage til polling, så
 * intet ser i stykker ud. Derfor måles det ægte kald.
 */
const fanget: Array<{ url: string; protocols?: string | string[] }> = []

class FalskSocket {
  constructor(url: string, protocols?: string | string[]) {
    fanget.push({ url, protocols })
  }
  close() { /* noop */ }
}

afterEach(() => { fanget.length = 0; vi.unstubAllGlobals() })

function aabn(cfg: { apiBaseUrl: string; authToken: string | null }) {
  vi.stubGlobal('WebSocket', FalskSocket as unknown as typeof WebSocket)
  openEventSocket(cfg)
  const sidste = fanget[fanget.length - 1]
  // Uden denne fejler `tsc` paa noUncheckedIndexedAccess — testene koerte
  // groent, men bygningen ville braekke.
  if (!sidste) throw new Error('openEventSocket aabnede ingen socket')
  return sidste
}

describe('event-socketen bærer legitimation', () => {
  it('sender tokenet som subprotokol', () => {
    const k = aabn({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'hemmelig' })  // noqa: literal-credential — proevedata, ordet «hemmelig»
    expect(k.protocols).toEqual([WS_SUBPROTOKOL, 'hemmelig'])
  })

  it('lægger ALDRIG tokenet i URLen', () => {
    // En query havner i serverens adgangslog ved hver forbindelse.
    const k = aabn({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'hemmelig' })  // noqa: literal-credential — proevedata, ordet «hemmelig»
    expect(k.url).not.toContain('hemmelig')
    expect(k.url).not.toContain('token=')
  })

  it('oversætter https til wss', () => {
    const k = aabn({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: 't' })
    expect(k.url).toBe('wss://api.srvlab.dk/ws')
  })

  it('uden token sendes ingen protokol', () => {
    // Serveren må ikke bekræfte en protokol der ikke bærer noget — og en
    // tom streng ville se ud som legitimation.
    const k = aabn({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: null })
    expect(k.protocols).toBeUndefined()
  })

  it('mellemrum omkring tokenet tæller ikke som et token', () => {
    const k = aabn({ apiBaseUrl: 'https://api.srvlab.dk/', authToken: '   ' })
    expect(k.protocols).toBeUndefined()
  })

  it('protokolnavnet er det serveren venter', () => {
    expect(WS_SUBPROTOKOL).toBe('jarvis-bearer')
  })
})
