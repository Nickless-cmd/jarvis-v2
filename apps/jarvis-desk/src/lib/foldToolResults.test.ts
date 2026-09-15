import { describe, it, expect } from 'vitest'
import { foldToolResults } from './foldToolResults'

describe('foldToolResults', () => {
  it('folder tool_result ind på matchende tool_use og fjerner tool_result-blokken', () => {
    const blocks = [
      { type: 'text', text: 'svar' },
      { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} },
      { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'a\nb' },
    ]
    const out = foldToolResults(blocks as any)
    expect(out.map((b: any) => b.type)).toEqual(['text', 'tool_use'])
    const tu = out.find((b: any) => b.type === 'tool_use') as any
    expect(tu.status).toBe('done')
    expect(tu.result).toBe('a\nb')
  })
  it('lader blokke uden tool_result være urørt', () => {
    const blocks = [{ type: 'text', text: 'x' }]
    expect(foldToolResults(blocks as any)).toEqual(blocks)
  })
  it('tool_result uden matchende tool_use droppes stille', () => {
    const blocks = [{ type: 'tool_result', tool_use_id: 'ukendt', status: 'done', content: 'y' }]
    expect(foldToolResults(blocks as any)).toEqual([])
  })
  it('bevarer progress-blokke (droppes ikke) med normaliseret status', () => {
    const blocks = [
      { type: 'text', text: 'svar' },
      { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} },
      { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'a' },
      { type: 'progress', tool_use_id: 'toolu_1', parent_tool_use_id: null, message: 'Kørte kommando', status: 'done' },
    ]
    const out = foldToolResults(blocks as any)
    const prog = out.find((b: any) => b.type === 'progress') as any
    expect(prog).toBeDefined()
    expect(prog.message).toBe('Kørte kommando')
    expect(prog.parent_tool_use_id).toBeNull()
    expect(prog.status).toBe('done')
  })
  it('normaliserer error-status på progress', () => {
    const blocks = [
      { type: 'progress', tool_use_id: 't1', parent_tool_use_id: null, message: 'Fejlede', status: 'error' },
    ]
    const out = foldToolResults(blocks as any)
    expect((out[0] as any).status).toBe('error')
  })

  // Målt 15/9-2026: Jarvis udgav et regneark med `publish_file`. Blokken blev
  // gemt i beskeden — med `url` og `kilde: "published"` og INTET attachment_id
  // — men typen fandtes ikke i denne kæde, så den blev droppet og filen nåede
  // aldrig skærmen.
  it('bevarer en UDGIVET fil — den bærer url, ikke attachment_id', () => {
    const blocks = [
      { type: 'file', filename: 'forbrug.xlsx', url: 'https://api.srvlab.dk/files/forbrug.xlsx', kilde: 'published', size_bytes: 8866 },
    ]
    const out = foldToolResults(blocks as any)
    expect(out).toHaveLength(1)
    expect(out[0]).toMatchObject({
      type: 'file',
      filename: 'forbrug.xlsx',
      url: 'https://api.srvlab.dk/files/forbrug.xlsx',
      kilde: 'published',
      size_bytes: 8866,
    })
  })

  it('bevarer et persisteret billede — reference, ikke src', () => {
    const blocks = [{ type: 'image', attachment_id: 'abc', filename: 'x.png', mime_type: 'image/png' }]
    const out = foldToolResults(blocks as any)
    expect(out).toHaveLength(1)
    expect(out[0]).toMatchObject({ type: 'image', attachment_id: 'abc', filename: 'x.png' })
  })

  it('en fil uden navn faar et brugbart fallback', () => {
    const out = foldToolResults([{ type: 'file', url: 'https://x/files/y' }] as any)
    expect((out[0] as any).filename).toBe('fil')
  })
})
