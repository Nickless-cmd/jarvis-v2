import { kompilérFlade } from './fladeProgram'
import { fladeStatus, settleKontrol, taelElementer, vaelgVisning } from './fladeVisning'

const box = (...born: unknown[]) => JSON.stringify({ type: 'box', title: 'T', children: born })

describe('kompilérFlade (DIL lag 3)', () => {
  it('lægger tekster i konstanttabellen og bygger et flat program', () => {
    const p = kompilérFlade(box({ type: 'callout', text: 'hej' }))
    expect(p?.program.map((i) => i.type)).toEqual(['box', 'callout'])
    expect(p?.konstanter).toContain('hej')
  })

  it('én fejl dræber ét element, ikke fladen', () => {
    const p = kompilérFlade(box({ type: 'callout', text: 'ok' }, { type: 'callout', text: '{#each nope som x}{x}{/each}' }))
    expect((p?.rod.children as unknown[]).length).toBe(1)
    expect(p?.diagnostik).toHaveLength(1)
  })

  it('roden fjernes ikke, selv når den selv fejler', () => {
    const p = kompilérFlade(JSON.stringify({ type: 'callout', text: '{#if }' }))
    expect(p?.rod.type).toBe('callout')
    expect(p?.diagnostik).toHaveLength(1)
  })

  it('trunkerer halv JSON til sidste komplette barn (S2)', () => {
    const p = kompilérFlade('{"type":"box","children":[{"type":"callout","text":"a"},{"type":"callout","te', true)
    expect(p?.trunkeret).toBe(true)
    expect((p?.rod.children as unknown[]).length).toBe(1)
  })

  it('roden trunkeres ikke: en halv rod uden type giver null', () => {
    expect(kompilérFlade('{"type":"bo', true)).toBeNull()
    // Ingen komplet konstruktion endnu => intet sikkert klippepunkt => intet at tegne (ikke en gættet rod)
    expect(kompilérFlade('{"type":"box","children":[', true)).toBeNull()
  })

  it('uden delvis er halv JSON null', () => {
    expect(kompilérFlade('{"type":"box","children":[', false)).toBeNull()
  })
})

describe('fladeVisning (DIL lag 4)', () => {
  it('lader det sidst virkende stå når det nye fejler', () => {
    expect(vaelgVisning(null, { a: 1 })).toEqual({ spec: { a: 1 }, fallback: true })
    expect(vaelgVisning({ b: 2 }, { a: 1 })).toEqual({ spec: { b: 2 }, fallback: false })
    expect(vaelgVisning(null, null)).toEqual({ spec: null, fallback: false })
  })

  it('S1: skiller kilden fra beskeden', () => {
    const b = { fallback: false, afvigelser: [] as string[] }
    expect(fladeStatus({ ...b, isSourceStreaming: true, hostMessageIsStreaming: true })).toBe('fladen skrives…')
    expect(fladeStatus({ ...b, isSourceStreaming: false, hostMessageIsStreaming: true })).toBe('fladen er færdig — beskeden skrives stadig')
    expect(fladeStatus({ ...b, isSourceStreaming: false, hostMessageIsStreaming: false })).toBeNull()
  })

  it('S3: finder elementer der ikke blev tegnet', () => {
    const p = kompilérFlade(box({ type: 'callout', text: 'a' }, { type: 'callout', text: 'b' }))!
    expect(taelElementer(p.rod)).toBe(3)
    expect(settleKontrol(p, p.rod, 'a b').ok).toBe(true)
    const r = settleKontrol(p, { type: 'box', children: [{ type: 'callout' }] }, 'a')
    expect(r.ok).toBe(false)
    expect(r.afvigelser[0]).toBe('1 af 3 elementer blev ikke tegnet')
    expect(settleKontrol(p, p.rod, '  ').afvigelser).toContain('fladen blev tegnet uden synlig tekst')
  })
})
