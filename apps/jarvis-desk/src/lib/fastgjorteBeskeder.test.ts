/**
 * Fastgjorte beskeder (Bjørn 18/9-2026: «pin skal kobles til noget rigtigt»).
 *
 * Knappen var ren `useState`: den farvede sig selv og glemte det. Det er
 * PERSISTENSEN der er selve rettelsen, så det er den testene holder fast i —
 * plus de to ting mobilens udgave allerede havde lært: pins hører til én
 * session, og de vises i samtalens rækkefølge, ikke i pin-rækkefølge.
 */
import { describe, expect, it, beforeEach } from 'vitest'
import { laesPins, skiftPin, ryd, pinnedeIRaekkefoelge } from './fastgjorteBeskeder'

describe('fastgjorte beskeder', () => {
  beforeEach(() => localStorage.clear())

  it('starter tom', () => {
    expect(laesPins('s1')).toEqual([])
  })

  it('slår fast og løs igen', () => {
    expect(skiftPin('s1', 'm1')).toEqual(['m1'])
    expect(skiftPin('s1', 'm2')).toEqual(['m1', 'm2'])
    expect(skiftPin('s1', 'm1')).toEqual(['m2'])
  })

  // Det her er hele pointen: overlever en genindlæsning.
  it('husker på tværs af læsninger', () => {
    skiftPin('s1', 'm1')
    expect(laesPins('s1')).toEqual(['m1'])
  })

  it('holder sessionerne adskilt', () => {
    skiftPin('s1', 'm1')
    expect(laesPins('s2')).toEqual([])
  })

  it('rydder', () => {
    skiftPin('s1', 'm1')
    ryd('s1')
    expect(laesPins('s1')).toEqual([])
  })

  it('et tomt besked-id fastgør ingenting', () => {
    expect(skiftPin('s1', '')).toEqual([])
  })

  it('tåler et ødelagt lager frem for at spærre samtalen', () => {
    localStorage.setItem('jarvis-desk:fastgjort:s1', '{ikke json')
    expect(laesPins('s1')).toEqual([])
  })

  it('kaster ikke-strenge væk', () => {
    localStorage.setItem('jarvis-desk:fastgjort:s1', JSON.stringify(['m1', 7, null, 'm2']))
    expect(laesPins('s1')).toEqual(['m1', 'm2'])
  })

  // Man leder efter en fastgjort besked dér hvor den STOD.
  it('giver dem i samtalens rækkefølge, ikke pin-rækkefølgen', () => {
    const beskeder = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]
    expect(pinnedeIRaekkefoelge(beskeder, ['c', 'a'])).toEqual([{ id: 'a' }, { id: 'c' }])
  })

  it('har et loft — en pin der rummer alt er ikke en pin', () => {
    for (let i = 0; i < 60; i++) skiftPin('s1', `m${i}`)
    const p = laesPins('s1')
    expect(p).toHaveLength(50)
    // De ÆLDSTE ryger. Den nyeste pin er den man lige satte.
    expect(p[p.length - 1]).toBe('m59')
    expect(p).not.toContain('m0')
  })
})
