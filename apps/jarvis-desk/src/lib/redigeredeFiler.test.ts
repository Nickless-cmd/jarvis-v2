import { describe, it, expect } from 'vitest'
import { redigeredeFiler, kortSti } from './redigeredeFiler'
import type { ContentBlock } from './sseProtocol'

const tool = (name: string, input: Record<string, unknown>, status: 'done' | 'error' = 'done'): ContentBlock =>
  ({ type: 'tool_use', id: `t-${name}-${JSON.stringify(input)}`, name, input, status })

describe('redigeredeFiler', () => {
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
