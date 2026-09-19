import { describe, it, expect } from 'vitest'
import { sektioner, sektionerTekst } from './livenessSektioner'
import type { ContentBlock } from './sseProtocol'

/** Byg en tool_use-blok, som reduceren ville have lavet den. */
function kald(name: string, i = 0): ContentBlock {
  return { type: 'tool_use', id: `t${i}`, name, input: {}, partialJson: '', status: 'running' } as ContentBlock
}

describe('livenessSektioner', () => {
  it('tom liste → ingen sektioner (ingen tomme skilletegn)', () => {
    expect(sektioner([], false)).toEqual([])
    expect(sektioner(undefined, false)).toEqual([])
    expect(sektioner(null, true)).toEqual([])
  })

  it('kun tool_use tælles — tekst og tænkning er ikke arbejde', () => {
    const blocks: ContentBlock[] = [
      { type: 'text', text: 'hej' } as ContentBlock,
      { type: 'thinking', thinking: 'hmm', seconds: 2 } as ContentBlock,
      kald('read_file', 1),
    ]
    expect(sektioner(blocks, false)).toEqual([{ key: 'read', tekst: 'Læste 1 fil' }])
  })

  it('ental og flertal er forskellige — «1 fil» mod «3 filer»', () => {
    expect(sektioner([kald('read_file', 0)], false)[0]?.tekst).toBe('Læste 1 fil')
    expect(
      sektioner([kald('read_file', 0), kald('read_file', 1), kald('read_file', 2)], false)[0]?.tekst,
    ).toBe('Læste 3 filer')
  })

  it('nutid mens han arbejder, datid når turen er slut — samme boolean for alle', () => {
    const blocks = [kald('read_file', 0), kald('bash', 1), kald('bash', 2)]
    expect(sektionerTekst(sektioner(blocks, true))).toBe('Læser 1 fil, kører 2 kommandoer')
    expect(sektionerTekst(sektioner(blocks, false))).toBe('Læste 1 fil, kørte 2 kommandoer')
  })

  it('rækkefølgen er CC’s — redigering før læsning før bash, uanset ankomst-rækkefølge', () => {
    // Bash ankommer FØRST, men skal stå sidst af de tre.
    const blocks = [kald('bash', 0), kald('read_file', 1), kald('edit_file', 2)]
    expect(sektionerTekst(sektioner(blocks, false))).toBe('Redigerede 1 fil, læste 1 fil, kørte 1 kommando')
  })

  it('kun FØRSTE sektion får stort begyndelsesbogstav', () => {
    const blocks = [kald('read_file', 0), kald('bash', 1)]
    const s = sektioner(blocks, false)
    expect(s[0]?.tekst.startsWith('L')).toBe(true)
    expect(s[1]?.tekst.startsWith('k')).toBe(true)
  })

  it('ukendt værktøj fanges af «andet» og står sidst — intet arbejde bliver usynligt', () => {
    const blocks = [kald('et_helt_nyt_vaerktoej', 0), kald('read_file', 1)]
    expect(sektionerTekst(sektioner(blocks, false))).toBe('Læste 1 fil, kaldte 1 værktøj')
  })

  it('operator-varianterne hører til samme familie som deres søskende', () => {
    const a = kald('read_file', 0)
    const b = kald('operator_read_file', 1)
    expect(sektioner([a, b], false)[0]?.tekst).toBe('Læste 2 filer')
  })

  it('familier uden antal gentages ikke — «tjekkede git» én gang for tre kald', () => {
    const blocks = [kald('git_status', 0), kald('git_diff', 1), kald('git_log', 2)]
    expect(sektionerTekst(sektioner(blocks, false))).toBe('Tjekkede git')
  })

  it('hukommelse og Centralen har egne sektioner', () => {
    const blocks = [kald('remember_this', 0), kald('central_query', 1)]
    expect(sektionerTekst(sektioner(blocks, false))).toBe('Huskede 1 ting, spurgte Centralen')
  })

  it('en blok uden navn kaster ikke — den havner i «andet»', () => {
    const blocks = [{ type: 'tool_use', id: 'x', name: '', input: {} } as ContentBlock]
    expect(() => sektioner(blocks, false)).not.toThrow()
  })
})
