import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

/**
 * Release-lytteren (push-vejen, 20/9-2026).
 *
 * Det der skal holdes fast er ikke at den kan forbinde — det er at den KUN
 * reagerer på sin egen begivenhed. `/ws` bærer hele event-bussen: indre stemme,
 * ræsonnements-konklusioner, private_brain. En lytter der vågner på alt andet
 * ville tjekke for opdateringer i ét væk, og det er værre end at vente.
 */

// vi.mock løftes over imports, så de fangede forbindelser skal bo i vi.hoisted —
// ellers er `instanser` ikke initialiseret når fabrikken kaldes.
const { instanser } = vi.hoisted(() => ({ instanser: [] as FakeSocket[] }))

interface FakeSocket {
  url: string
  opts: { headers?: Record<string, string> } | undefined
  handlers: Record<string, ((...a: unknown[]) => void)[]>
  on: (ev: string, cb: (...a: unknown[]) => void) => FakeSocket
  emit: (ev: string, ...a: unknown[]) => void
}

vi.mock('ws', () => {
  class FakeWebSocket implements FakeSocket {
    handlers: Record<string, ((...a: unknown[]) => void)[]> = {}
    constructor(public url: string, public opts?: { headers?: Record<string, string> }) {
      instanser.push(this)
    }
    on(ev: string, cb: (...a: unknown[]) => void): FakeWebSocket {
      ;(this.handlers[ev] ||= []).push(cb)
      return this
    }
    emit(ev: string, ...a: unknown[]): void {
      for (const cb of this.handlers[ev] || []) cb(...a)
    }
    ping(): void { /* ingen rigtig socket */ }
    removeAllListeners(): void { this.handlers = {} }
    terminate(): void { /* ingen rigtig socket */ }
  }
  return { default: FakeWebSocket }
})

import { startReleaseLytter } from './appRelease'

let aabne: { luk: () => void }[] = []

function start(overrides: Partial<Parameters<typeof startReleaseLytter>[0]> = {}) {
  const set: Record<string, unknown>[] = []
  const lytter = startReleaseLytter({
    apiBaseUrl: 'https://api.srvlab.dk',
    authToken: 'tok-123', // noqa: literal-credential
    onRelease: (info) => set.push(info),
    ...overrides,
  })
  aabne.push(lytter)
  return { lytter, set, socket: instanser[instanser.length - 1] }
}

beforeEach(() => {
  instanser.length = 0
  aabne = []
})

afterEach(() => {
  // luk() rydder reconnect-timeren; uden det holder en planlagt genforbindelse
  // testprocessen i live.
  for (const l of aabne) l.luk()
})

describe('release-lytteren', () => {
  it('forbinder til /ws og bærer tokenet i Authorization-headeren', () => {
    const { socket } = start()
    expect(socket.url).toBe('wss://api.srvlab.dk/ws')
    expect(socket.opts?.headers?.Authorization).toBe('Bearer tok-123')
  })

  it('udelader headeren når der ikke er et token', () => {
    const { socket } = start({ authToken: null })
    expect(socket.opts?.headers?.Authorization).toBeUndefined()
  })

  it('kalder onRelease når serveren melder app.release.available', () => {
    const { set, socket } = start()
    socket.emit('message', JSON.stringify({ kind: 'app.release.available', payload: { version: '0.6.60' } }))
    expect(set).toEqual([{ version: '0.6.60' }])
  })

  it('IGNORERER alle andre begivenheder på bussen', () => {
    const { set, socket } = start()
    // /ws bærer hele bussen — de her må ikke vække updateren.
    for (const kind of ['inner.voice', 'reasoning.conclusion', 'private_brain.record', 'release.available']) {
      socket.emit('message', JSON.stringify({ kind, payload: { version: '9.9.9' } }))
    }
    expect(set).toEqual([])
  })

  it('overlever uforståelig trafik uden at kaste', () => {
    const { set, socket } = start()
    expect(() => socket.emit('message', 'ikke json')).not.toThrow()
    expect(() => socket.emit('message', JSON.stringify({ uden: 'kind' }))).not.toThrow()
    expect(set).toEqual([])
  })

  it('luk() river forbindelsen ned og fjerner lytterne', () => {
    const { socket } = start()
    const lytter = aabne[aabne.length - 1]
    expect(Object.keys(socket.handlers).length).toBeGreaterThan(0)
    lytter.luk()
    aabne = [] // afterEach skal ikke lukke den igen
    expect(socket.handlers).toEqual({})
  })
})
