import { describe, it, expect, vi } from 'vitest'
import { visAendring, paaAendringsFokus } from './aendringsFokus'

describe('aendringsFokus', () => {
  it('bærer stien frem til lytteren', () => {
    const set = vi.fn()
    const stop = paaAendringsFokus(set)
    visAendring('src/a.ts')
    expect(set).toHaveBeenCalledWith('src/a.ts')
    stop()
  })

  it('afmelding virker — ellers ville en lukket visning blive ved med at lytte', () => {
    const set = vi.fn()
    paaAendringsFokus(set)()
    visAendring('src/a.ts')
    expect(set).not.toHaveBeenCalled()
  })

  it('én lytter der kaster vælter ikke de andre', () => {
    const god = vi.fn()
    const stop1 = paaAendringsFokus(() => { throw new Error('nej') })
    const stop2 = paaAendringsFokus(god)
    visAendring('src/a.ts')
    expect(god).toHaveBeenCalledWith('src/a.ts')
    stop1(); stop2()
  })
})
