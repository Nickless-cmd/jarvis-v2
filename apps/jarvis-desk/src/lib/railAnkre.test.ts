import { describe, expect, it } from 'vitest'
import { bygRailAnkre, KORT_SESSION } from './railAnkre'

const tekst = (t: string) => [{ type: 'text', text: t }]
const bruger = (id: string, t = id) => ({ id, role: 'user', content: tekst(t) })
const svar = (id: string, content: unknown = tekst('ok')) => ({ id, role: 'assistant', content })
const markoer = (id: string, created_at = '2026-09-13T16:51:20+00:00') =>
  ({ id, role: 'compact_marker', content: tekst('Samtalen blev komprimeret'), created_at })

/** n ture: u0,a0,u1,a1,… */
function ture(n: number) {
  return Array.from({ length: n }, (_, i) => [bruger(`u${i}`), svar(`a${i}`)]).flat()
}

describe('bygRailAnkre', () => {
  it('kort session: én streg pr. tur', () => {
    const r = bygRailAnkre(ture(3), [])
    expect(r.map((a) => a.id)).toEqual(['u0', 'u1', 'u2'])
    expect(r.every((a) => a.slags === 'kapitel')).toBe(true)
  })

  it('lang session uden kapitler: INGEN streg pr. besked (det var støjen)', () => {
    expect(bygRailAnkre(ture(KORT_SESSION + 1), [])).toEqual([])
  })

  it('lang session: kun kapitlerne, med serverens titler', () => {
    const r = bygRailAnkre(ture(40), [
      { anchor_id: 'u0', title: 'Godmorgen' },
      { anchor_id: 'u17', title: 'Sandbox fejl' },
      { anchor_id: 'findes-ikke', title: 'Gammel' },
    ])
    expect(r.map((a) => [a.id, a.label])).toEqual([['u0', 'Godmorgen'], ['u17', 'Sandbox fejl']])
  })

  it('kapitlet arver fejl fra turen', () => {
    const b = ture(10)
    b[3] = svar('a1', [{ type: 'tool_use', status: 'error' }])
    const r = bygRailAnkre(b, [{ anchor_id: 'u1', title: 'X' }])
    expect(r[0]!.fejl).toBe(true)
  })

  it('komprimering peger på første synlige besked efter markøren', () => {
    const b = [...ture(8)]
    b.splice(6, 0, markoer('compact-1'))    // efter a2, før u3
    const r = bygRailAnkre(b, [{ anchor_id: 'u0', title: 'Start' }])
    const k = r.find((a) => a.slags === 'komprimering')!
    expect(k.id).toBe('u3')
    expect(k.label).toMatch(/^Komprimeret · 13\/9 \d\d:51$/)
  })

  it('rækkefølge: komprimering før et kapitel på samme besked, og i skærm-orden', () => {
    const b = [...ture(8)]
    b.splice(6, 0, markoer('compact-1'))
    const r = bygRailAnkre(b, [
      { anchor_id: 'u5', title: 'Senere' },
      { anchor_id: 'u3', title: 'Efter komprimering' },
      { anchor_id: 'u0', title: 'Start' },
    ])
    expect(r.map((a) => `${a.slags}:${a.id}`)).toEqual([
      'kapitel:u0', 'komprimering:u3', 'kapitel:u3', 'kapitel:u5',
    ])
  })

  it('to markører i træk (målt: par 10 s fra hinanden) = ÉN streg på næste SYNLIGE besked, seneste tid', () => {
    const b = [bruger('u0'), svar('a0'), markoer('c1', '2026-09-14T15:09:44+00:00'),
      markoer('c2', '2026-09-14T15:19:54+00:00'), bruger('u1'), svar('a1')]
    const k = bygRailAnkre(b, []).filter((a) => a.slags === 'komprimering')
    expect(k.map((a) => a.id)).toEqual(['u1'])
    expect(k[0]!.label).toMatch(/:19$/)
  })

  it('markør til sidst uden besked efter: ingen streg', () => {
    const r = bygRailAnkre([...ture(2), markoer('c')], [])
    expect(r.some((a) => a.slags === 'komprimering')).toBe(false)
  })

  it('komprimering vises også i en kort session', () => {
    const b = [bruger('u0'), svar('a0'), markoer('c'), bruger('u1'), svar('a1')]
    expect(bygRailAnkre(b, []).map((a) => a.slags)).toEqual(['kapitel', 'komprimering', 'kapitel'])
  })
})
