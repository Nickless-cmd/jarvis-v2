import { describe, it, expect, vi } from 'vitest'
import { lavVaerdiLager } from './vaerdiLager'

describe('vaerdiLager', () => {
  it('giver sidste værdi og kalder abonnenter ved en NY værdi', () => {
    const l = lavVaerdiLager({ n: 1 })
    const f = vi.fn()
    const af = l.abonner(f)
    const ny = { n: 2 }
    l.saet(ny)
    expect(l.hent()).toBe(ny)
    expect(f).toHaveBeenCalledTimes(1)
    af()
    l.saet({ n: 3 })
    expect(f).toHaveBeenCalledTimes(1)
  })

  it('samme værdi igen notificerer ingen — ellers renderede alle abonnenter om for intet', () => {
    const v = { n: 1 }
    const l = lavVaerdiLager(v)
    const f = vi.fn()
    l.abonner(f)
    l.saet(v)
    expect(f).not.toHaveBeenCalled()
  })
})
