/**
 * Opdaterings-knappen: en ventende worker SKAL meldes, også uden en aktiv controller.
 *
 * Målt 9/10-2026 (side-885a39ab9e / side-1038357920): `navigator.serviceWorker.controller`
 * er null på en frisk load — den sættes først når en worker har taget over. Kravet om
 * den skjulte derfor knappen, og klienten kørte videre på det gamle build i det uendelige
 * (railen blev ved med at vise den gamle CSS selvom serveren sendte den nye).
 *
 * `registration.waiting` er den rigtige betingelse: den er KUN sat ved en ægte opdatering —
 * ved første installation går workeren direkte til `activated` uden at vente.
 */
import { afterEach, describe, expect, it, vi } from 'vitest'

import { registerPwa } from './register'

function _stub(sw: unknown) {
  Object.defineProperty(navigator, 'serviceWorker', { configurable: true, value: sw })
}

describe('registerPwa', () => {
  afterEach(() => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = undefined
  })

  it('melder en ventende worker selvom controller er null', async () => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = true
    const ventende = { state: 'installed' }
    const reg = {
      waiting: ventende,
      installing: null,
      addEventListener: () => {},
      update: () => Promise.resolve(),
    }
    _stub({ register: () => Promise.resolve(reg), controller: null })
    const set = vi.fn()
    const stop = registerPwa(set)
    await new Promise((r) => setTimeout(r, 0))
    expect(set).toHaveBeenCalledWith(ventende)
    stop()
  })

  it('melder intet når der ikke venter en worker', async () => {
    ;(globalThis as Record<string, unknown>).__WEB_BUILD__ = true
    const reg = {
      waiting: null,
      installing: null,
      addEventListener: () => {},
      update: () => Promise.resolve(),
    }
    _stub({ register: () => Promise.resolve(reg), controller: null })
    const set = vi.fn()
    const stop = registerPwa(set)
    await new Promise((r) => setTimeout(r, 0))
    expect(set).not.toHaveBeenCalled()
    stop()
  })
})
