import { describe, expect, it } from 'vitest'
import { udenErstattede } from './gensendDublet'

describe('udenErstattede', () => {
  const liste = [
    { id: 'm1', role: 'user' },
    { id: 'm2', role: 'assistant' },
    { id: 'u-5', role: 'user' },
  ]
  it('skjuler den gamle boble efter gensend — kun den nye bruger-besked står', () => {
    const ud = udenErstattede(liste, new Set(['m1']))
    expect(ud.map((m) => m.id)).toEqual(['m2', 'u-5'])
    expect(ud.filter((m) => m.role === 'user')).toHaveLength(1)
  })
  it('rører intet uden gensend (normal send)', () => {
    expect(udenErstattede(liste, new Set())).toBe(liste)
  })
})
