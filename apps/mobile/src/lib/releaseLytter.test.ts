import { releaseUrl, startReleaseLytter, GENFORBIND_MS } from './releaseLytter'
import type { WebSocketLignende } from './broKlient'

/**
 * Mobilens release-lytter.
 *
 * Hele grunden til at den findes: uden den sker der INTET før man går ud og
 * ind af appen. Testene måler derfor det der faktisk var i stykker — at en
 * besked på bussen udløser et opdateringstjek mens appen bare ligger åben.
 */

function lavFalskSocket() {
  const s: WebSocketLignende & { lukket: boolean; sendt: string[] } = {
    lukket: false,
    sendt: [],
    send(d: string) { this.sendt.push(d) },
    close() { this.lukket = true },
    onopen: null,
    onclose: null,
    onerror: null,
    onmessage: null,
  }
  return s
}

/** Henter et element og fejler hoejlydt hvis det ikke findes — bedre end et
 *  blindt `!`, for saa staar der HVAD der manglede naar en test knaekker. */
function nr<T>(liste: T[], i: number): T {
  const v = liste[i]
  if (v === undefined) throw new Error(`der var intet element ${i} (kun ${liste.length})`)
  return v
}

function opsaet(overstyr: Record<string, unknown> = {}) {
  const sockets: ReturnType<typeof lavFalskSocket>[] = []
  const planlagt: { fn: () => void; ms: number }[] = []
  const onRelease = jest.fn()
  const urls: string[] = []
  const muligheder: unknown[] = []
  const lytter = startReleaseLytter({
    apiBaseUrl: 'https://api.eksempel.dk',
    authToken: 'et-token',
    onRelease,
    lavSocket: (url, m) => {
      urls.push(url)
      muligheder.push(m)
      const s = lavFalskSocket()
      sockets.push(s)
      return s
    },
    planlaeg: (fn, ms) => { planlagt.push({ fn, ms }); return planlagt.length },
    ryd: () => {},
    ...overstyr,
  })
  return { lytter, sockets, planlagt, onRelease, urls, muligheder }
}

describe('releaseUrl', () => {
  it('peger paa event-bussen i roden, ikke paa bro-kanalen', () => {
    // broKlient bruger `api/jarvisx-bridge/ws` — en ANDEN kanal. Bussen
    // ligger paa `/ws` (APIRouter uden prefix i routes/live.py).
    expect(releaseUrl('https://api.eksempel.dk')).toBe('wss://api.eksempel.dk/ws')
  })

  it('taaler en skraastreg til sidst', () => {
    expect(releaseUrl('https://api.eksempel.dk/')).toBe('wss://api.eksempel.dk/ws')
  })

  it('bliver til ws for et usikkert endepunkt', () => {
    expect(releaseUrl('http://10.0.0.39:8000')).toBe('ws://10.0.0.39:8000/ws')
  })
})

describe('startReleaseLytter', () => {
  it('sender token i HEADEREN — uden den lukker serveren forbindelsen', () => {
    const { muligheder } = opsaet()
    expect(muligheder[0]).toEqual({ headers: { Authorization: 'Bearer et-token' } })
  })

  it('udloeser et opdateringstjek naar releasen kommer paa bussen', () => {
    const { sockets, onRelease } = opsaet()
    nr(sockets, 0).onopen?.()
    nr(sockets, 0).onmessage?.({ data: JSON.stringify({ kind: 'app.release.available' }) })
    expect(onRelease).toHaveBeenCalledTimes(1)
  })

  it('ignorerer resten af bussen — den baerer ALT', () => {
    const { sockets, onRelease } = opsaet()
    nr(sockets, 0).onopen?.()
    for (const kind of ['runtime.tick', 'inner_voice.signal', 'memory.sensory.recorded']) {
      nr(sockets, 0).onmessage?.({ data: JSON.stringify({ kind }) })
    }
    nr(sockets, 0).onmessage?.({ data: 'ikke json overhovedet' })
    nr(sockets, 0).onmessage?.({ data: JSON.stringify({ type: 'ping' }) })
    expect(onRelease).not.toHaveBeenCalled()
  })

  it('en fejl i kalderen draeber ikke forbindelsen', () => {
    // Ellers ville ÉT daarligt opdateringstjek koste alle de foelgende.
    const sprang = jest.fn(() => { throw new Error('checkForUpdate braekkede') })
    const { sockets } = opsaet({ onRelease: sprang })
    nr(sockets, 0).onopen?.()
    const besked = { data: JSON.stringify({ kind: 'app.release.available' }) }
    expect(() => nr(sockets, 0).onmessage?.(besked)).not.toThrow()
    nr(sockets, 0).onmessage?.(besked)
    expect(sprang).toHaveBeenCalledTimes(2)
  })

  it('genforbinder med voksende pause naar forbindelsen falder', () => {
    const { sockets, planlagt } = opsaet()
    nr(sockets, 0).onclose?.()
    expect(nr(planlagt, 0).ms).toBe(GENFORBIND_MS[0])
    nr(planlagt, 0).fn()
    nr(sockets, 1).onclose?.()
    expect(nr(planlagt, 1).ms).toBe(GENFORBIND_MS[1])
  })

  it('nulstiller pausen naar forbindelsen lykkes igen', () => {
    const { sockets, planlagt } = opsaet()
    nr(sockets, 0).onclose?.()
    nr(planlagt, 0).fn()
    nr(sockets, 1).onopen?.()          // den kom igennem
    nr(sockets, 1).onclose?.()
    expect(nr(planlagt, 1).ms).toBe(GENFORBIND_MS[0])
  })

  it('stop() genforbinder ikke — ellers levede lytteren videre efter logud', () => {
    const { lytter, sockets, planlagt } = opsaet()
    const foer = planlagt.length
    lytter.stop()
    nr(sockets, 0).onclose?.()
    expect(planlagt.length).toBe(foer)
    expect(nr(sockets, 0).lukket).toBe(true)
  })

  it('melder om den er forbundet', () => {
    const { lytter, sockets } = opsaet()
    expect(lytter.erForbundet()).toBe(false)
    nr(sockets, 0).onopen?.()
    expect(lytter.erForbundet()).toBe(true)
    nr(sockets, 0).onclose?.()
    expect(lytter.erForbundet()).toBe(false)
  })
})
