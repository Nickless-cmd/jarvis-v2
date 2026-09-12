
import { arbejdsLinje } from './arbejdsLinje'
import type { ContentBlock } from './sseProtocol'

const tanke = (t: string): ContentBlock => ({ type: 'thinking', thinking: t })
const tekst = (t: string): ContentBlock => ({ type: 'text', text: t })
const vaerktoej = (status: string, navn = 'bash', input: unknown = { command: 'sleep 270' }): ContentBlock =>
  ({ type: 'tool_use', id: 't1', name: navn, input, status } as ContentBlock)

describe('arbejdsLinje', () => {
  it('viser værktøjets metadata mens kommandoen kører', () => {
    // DET var fejlen: her stod den fem minutter gamle tanke og så stallet ud.
    const ud = arbejdsLinje([tanke('Jeg kører testene nu'), vaerktoej('running')], 0)
    expect(ud).toContain('sleep')
    expect(ud).not.toContain('Jeg kører testene nu')
  })

  it('siger «Arbejder» når værktøjet er færdigt og modellen ikke har talt endnu', () => {
    const ud = arbejdsLinje([tanke('en tanke'), vaerktoej('done')], 0)
    expect(ud.startsWith('Arbejder')).toBe(true)
  })

  it('vender tilbage til tankestrømmen når han tænker videre efter værktøjet', () => {
    const ud = arbejdsLinje(
      [tanke('gammel'), vaerktoej('done'), tanke('Nu ser jeg på resultatet')], 0)
    expect(ud).toContain('Nu ser jeg')
  })

  it('lader ikke svarteksten overtage linjen', () => {
    // Teksten står allerede i tråden; gentages den her, siger linjen intet om
    // arbejdet.
    const ud = arbejdsLinje([tanke('Jeg undersøger sagen'), tekst('Her er svaret.')], 0)
    expect(ud).toContain('Jeg undersøger')
    expect(ud).not.toContain('Her er svaret')
  })

  it('falder tilbage til «Tænker» med prikker når der intet er endnu', () => {
    expect(arbejdsLinje([], 0).startsWith('Tænker')).toBe(true)
    expect(arbejdsLinje(null, 0).startsWith('Tænker')).toBe(true)
  })

  it('prikkerne skifter med trinnet, så linjen lever uden at flimre', () => {
    const a = arbejdsLinje([], 0)
    const b = arbejdsLinje([], 1)
    expect(a).not.toBe(b)
  })

  it('«Arbejder» har prikke-sekvensen — det var det Bjørn bad om', () => {
    // «vise endten tools meta data eller arbejder. .. ...»
    const set = new Set([0, 1, 2].map((t) => arbejdsLinje([vaerktoej('done')], t)))
    expect(set.size).toBe(3)
    for (const s of set) expect(s).toMatch(/^Arbejder\.+/)
  })

  it('en tom tanke skygger ikke for det der faktisk skete', () => {
    // En tanke-blok uden indhold er ikke noget han laver. Godtages den, taber
    // vi værktøjet der står lige før den.
    const ud = arbejdsLinje([vaerktoej('running'), tanke('   ')], 0)
    expect(ud).toContain('sleep')
  })

  it('en foreløbig række regnes som kørende og bruger serverens egen etiket', () => {
    // Målt på telefonen: rækken i tråden sagde «Kører kommando: sleep» mens
    // linjen sagde «Kører bash…» — samme værktøj, to sandheder. Etiketten
    // ligger allerede i working_step; den skulle bare bruges.
    const b = { type: 'tool_use', id: '', name: 'bash', input: {},
                foreloebig: { startet: 0, skridt: 1, etiket: 'Kører kommando: sleep' } } as ContentBlock
    expect(arbejdsLinje([b], 0)).toBe('Kører kommando: sleep')
  })

  it('uden serverens etiket beskrives værktøjet ud fra argumenterne', () => {
    const b = { type: 'tool_use', id: 't', name: 'bash', input: { command: 'ls -la' },
                status: 'running' } as ContentBlock
    expect(arbejdsLinje([b], 0)).toContain('ls')
  })
})
