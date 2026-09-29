import { describe, it, expect } from 'vitest'
import { redigeredeFiler, maalteRedigeringer, redigeredeDiffPar, kortSti } from './redigeredeFiler'
import type { ContentBlock } from './sseProtocol'

const tool = (name: string, input: Record<string, unknown>, status: 'done' | 'error' = 'done'): Extract<ContentBlock, { type: 'tool_use' }> =>
  ({ type: 'tool_use', id: `t-${name}-${JSON.stringify(input)}`, name, input, status })

describe('redigeredeFiler', () => {
  it('summerer målte ændringer pr. fil og skjuler delvise tal', () => {
    const blocks: ContentBlock[] = [
      { ...tool('edit_file', { path: 'a.ts' }), result: '{"linjer_tilfoejet":5,"linjer_fjernet":2}' },
      { ...tool('edit_file', { path: 'a.ts' }), result: '{"linjer_tilfoejet":3,"linjer_fjernet":1}' },
      tool('edit_file', { path: 'b.ts' }),
      { ...tool('edit_file', { path: 'c.ts' }), result: '{"linjer_tilfoejet":1,"linjer_fjernet":0}' },
      tool('edit_file', { path: 'c.ts' }),
    ]
    expect(maalteRedigeringer(blocks)).toEqual({ 'a.ts': { added: 8, removed: 3 } })
  })

  it('regner af kaldets EGNE par når serveren ikke har målt (operator-kald)', () => {
    // Bjørn 29/9-2026: «feltet under mangler +xx -xx ved filerne uanset om de
    // er redigeret på din container eller min maskine». `operator_*` kører på
    // hans maskine, hvor vi ikke har filen i hånden — der findes ingen
    // server-målte tal for dem, så uden faldbacken stod filen uden tal.
    const blocks: ContentBlock[] = [
      tool('operator_edit_file', { path: '/home/bs/x.ts', old_text: 'a\nb', new_text: 'a\nb\nc' }),
    ]
    expect(maalteRedigeringer(blocks)).toEqual({ '/home/bs/x.ts': { added: 3, removed: 2 } })
  })
  it('finder de filer der blev SKREVET', () => {
    const ud = redigeredeFiler([
      tool('write_file', { path: 'src/a.ts' }),
      tool('edit_file', { file_path: 'src/b.ts' }),
    ])
    expect(ud.map((f) => f.path)).toEqual(['src/a.ts', 'src/b.ts'])
  })

  it('læsning og søgning er ikke redigering', () => {
    expect(redigeredeFiler([
      tool('read_file', { path: 'src/a.ts' }),
      tool('grep', { path: 'src' }),
      tool('list_dir', { path: 'src' }),
    ])).toEqual([])
  })

  it('samme fil to gange er ÉN fil', () => {
    // Ellers ville en fil der rettes tre gange fylde tre rækker og se ud
    // som tre filer.
    const ud = redigeredeFiler([
      tool('edit_file', { path: 'src/a.ts' }),
      tool('edit_file', { path: 'src/a.ts' }),
    ])
    expect(ud).toEqual([{ path: 'src/a.ts', gange: 2 }])
  })

  it('et FEJLET kald har ikke redigeret noget', () => {
    // At tælle det ville love en ændring der ikke findes.
    expect(redigeredeFiler([tool('write_file', { path: 'src/a.ts' }, 'error')])).toEqual([])
  })

  it('et kald uden sti tælles ikke', () => {
    expect(redigeredeFiler([tool('write_file', {})])).toEqual([])
  })

  it('operator-varianterne tæller med — de skriver på hans maskine', () => {
    const ud = redigeredeFiler([tool('operator_write_file', { path: '/home/bs/x.ts' })])
    expect(ud.map((f) => f.path)).toEqual(['/home/bs/x.ts'])
  })

  it('tekst- og tanke-blokke forstyrrer ikke', () => {
    const blandet = [
      { type: 'text', text: 'skriver nu write_file til src/a.ts' },
      tool('write_file', { path: 'src/a.ts' }),
    ] as ContentBlock[]
    expect(redigeredeFiler(blandet)).toEqual([{ path: 'src/a.ts', gange: 1 }])
  })
})

describe('kortSti', () => {
  it('beholder de to sidste led — filnavnet er det der skiller', () => {
    expect(kortSti('/media/projects/jarvis-v2/apps/jarvis-desk/src/a.ts')).toBe('src/a.ts')
    expect(kortSti('a.ts')).toBe('a.ts')
    expect(kortSti('src/a.ts')).toBe('src/a.ts')
  })
})

describe('redigeredeDiffPar', () => {
  it('giver parrene bag hover-diffen — samme kilde som tallene', () => {
    // Bjørn 29/9-2026: «hvis jeg holder musen over fil navnet i feltet så
    // kommer der en diff visning med scrool». Diffen bygges af kaldets EGNE
    // par, fordi serverens målte tal kun er tal — de bærer ingen linjer.
    const par = redigeredeDiffPar([
      tool('edit_file', { path: 'a.ts', old_text: 'gammel', new_text: 'ny' }),
    ])
    expect(par).toEqual({ 'a.ts': [{ gammel: 'gammel', ny: 'ny' }] })
  })

  it('samler flere redigeringer af samme fil i rækkefølge', () => {
    const par = redigeredeDiffPar([
      tool('edit_file', { path: 'a.ts', old_text: 'v1', new_text: 'v2' }),
      tool('edit_file', { path: 'a.ts', old_text: 'v2', new_text: 'v3' }),
    ])
    expect(par['a.ts']).toEqual([
      { gammel: 'v1', ny: 'v2' },
      { gammel: 'v2', ny: 'v3' },
    ])
  })

  it('multi_edit bærer sine par i edits[]', () => {
    const par = redigeredeDiffPar([
      tool('multi_edit', { path: 'a.ts', edits: [
        { old_text: 'x', new_text: 'y' },
        { old_text: 'p', new_text: 'q' },
      ] }),
    ])
    expect(par['a.ts']).toEqual([{ gammel: 'x', ny: 'y' }, { gammel: 'p', ny: 'q' }])
  })

  it('operator-varianten giver også par — den skriver på hans maskine', () => {
    const par = redigeredeDiffPar([
      tool('operator_edit_file', { path: '/home/bs/x.ts', old_text: 'a', new_text: 'b' }),
    ])
    expect(par['/home/bs/x.ts']).toEqual([{ gammel: 'a', ny: 'b' }])
  })

  it('et FEJLET kald giver ingen diff', () => {
    expect(redigeredeDiffPar([
      tool('edit_file', { path: 'a.ts', old_text: 'a', new_text: 'b' }, 'error'),
    ])).toEqual({})
  })

  it('læsning giver ingen diff', () => {
    expect(redigeredeDiffPar([tool('read_file', { path: 'a.ts' })])).toEqual({})
  })
})
