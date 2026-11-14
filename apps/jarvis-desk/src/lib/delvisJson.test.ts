import { describe, expect, it } from 'vitest'
import { erDelvis, reparérDelvisJson } from './delvisJson'

const p = (s: string) => JSON.parse(reparérDelvisJson(s) as string)

describe('reparérDelvisJson', () => {
  it('tegner de KOMPLETTE rækker af en tabel der stadig skrives', () => {
    const halv = '{"type":"table","columns":["Land","Salg"],"rows":[["DK",12],["SE",8'
    const ud = p(halv)
    expect(ud.type).toBe('table')
    expect(ud.columns).toEqual(['Land', 'Salg'])
    // Kun den række der er bevisligt færdig. `["SE",8` kan blive `89`.
    expect(ud.rows).toEqual([['DK', 12]])
  })

  it('opfinder ALDRIG et tal — det halve element klippes væk', () => {
    const ud = p('{"rows":[["DK",12],["SE",8')
    expect(ud.rows).toHaveLength(1)
    expect(JSON.stringify(ud)).not.toContain('89')
    expect(JSON.stringify(ud)).not.toContain('"SE"')
  })

  it('beholder et helt element selv uden komma efter', () => {
    const ud = p('{"items":[{"a":1}],"titel":"x')
    expect(ud.items).toEqual([{ a: 1 }])
  })

  it('lukker indlejrede strukturer i den rigtige rækkefølge', () => {
    const ud = p('{"box":{"children":[{"type":"stats","items":[{"label":"A","value":1},')
    expect(ud.box.children).toHaveLength(1)
    expect(ud.box.children[0].items).toEqual([{ label: 'A', value: 1 }])
  })

  it('afviser ubalanceret input frem for at gætte', () => {
    expect(reparérDelvisJson('{"a":1}}')).toBeNull()
    expect(reparérDelvisJson(']{"a":1}')).toBeNull()
  })

  it('afviser input uden et sikkert klippepunkt', () => {
    expect(reparérDelvisJson('{"type":"table"')).toBeNull()
    expect(reparérDelvisJson('{"rows":[["DK"')).toBeNull()
    expect(reparérDelvisJson('')).toBeNull()
    expect(reparérDelvisJson('ikke json')).toBeNull()
  })

  it('en afsluttet streng inde i en streng taeller ikke som struktur', () => {
    // `}` inde i en tekst må ikke lukke objektet.
    const ud = p('{"title":"Salg } i alt","rows":[["DK",1],"SE')
    expect(ud.title).toBe('Salg } i alt')
    expect(ud.rows).toEqual([['DK', 1]])
  })

  it('escapet citationstegn brækker ikke streng-sporingen', () => {
    const ud = p('{"title":"han sagde \\"hej\\"","rows":[["DK",1],["SE"')
    expect(ud.title).toBe('han sagde "hej"')
    expect(ud.rows).toEqual([['DK', 1]])
  })
})

describe('erDelvis', () => {
  it('en blok uden afsluttende klampe er delvis', () => {
    expect(erDelvis('{"a":1')).toBe(true)
    expect(erDelvis('{"a":1}')).toBe(false)
    expect(erDelvis('[1,2]')).toBe(false)
    expect(erDelvis('')).toBe(false)
  })
})
