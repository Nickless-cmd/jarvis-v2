import { describe, it, expect } from 'vitest'
import { streamReducer, initialStreamState } from './streamReducer'
import { denseBlocks, lastTextBlock } from './blockHelpers'

// Regression (Bjørn 9. jul, sort skærm under streaming): når serveren sender
// tool_result som content-blok på et NYT index, folder reduceren det ind på
// tool_use'en men fylder ALDRIG sit eget index → en efterfølgende tekst-blok på
// et højere index efterlader et undefined-hul. `[...blocks].find(b=>b.type)`
// crashede på hullet → React unmount → sort app. Disse tests bevogter mod det.
describe('sparse-hole robusthed (tool_result content-blok)', () => {
  function buildSparse() {
    let s = initialStreamState()
    s = streamReducer(s, { type: 'message_start', message: { id: 'r1', model: '', provider: '', lane: '', session_id: null, usage: { input_tokens: 0, output_tokens: 0 } } } as never)
    s = streamReducer(s, { type: 'content_block_start', index: 0, content_block: { type: 'text', text: '' } } as never)
    s = streamReducer(s, { type: 'content_block_delta', index: 0, delta: { type: 'text_delta', text: 'lad mig tjekke' } } as never)
    s = streamReducer(s, { type: 'content_block_start', index: 1, content_block: { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} } } as never)
    // tool_result content-blok på index 2 → foldes ind på tool_use, index 2 aldrig fyldt
    s = streamReducer(s, { type: 'content_block_start', index: 2, content_block: { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'ok' } } as never)
    // efterfølgende tekst på index 3 → efterlader hul på index 2
    s = streamReducer(s, { type: 'content_block_start', index: 3, content_block: { type: 'text', text: '' } } as never)
    s = streamReducer(s, { type: 'content_block_delta', index: 3, delta: { type: 'text_delta', text: 'færdig' } } as never)
    return s
  }

  it('reduceren efterlader et sparsomt hul (dokumenterer roden)', () => {
    const s = buildSparse()
    // index 2 er et hul; spread densificerer det til undefined
    expect([...s.blocks][2]).toBeUndefined()
  })

  it('denseBlocks fjerner hullet uden at kaste', () => {
    const s = buildSparse()
    const dense = denseBlocks(s.blocks)
    expect(dense.every((b) => !!b)).toBe(true)
    // tool_use bærer det foldede resultat; to tekst-blokke + ét tool_use
    expect(dense.filter((b) => b.type === 'text').length).toBe(2)
    const tu = dense.find((b) => b.type === 'tool_use') as { result?: string; status?: string }
    expect(tu.result).toBe('ok')
    expect(tu.status).toBe('done')
  })

  it('lastTextBlock er null-safe mod hullet (var crash-stedet)', () => {
    const s = buildSparse()
    // FØR fix: [...blocks].reverse().find(b => b.type==='text') kastede på undefined
    expect(() => lastTextBlock(s.blocks)).not.toThrow()
    expect(lastTextBlock(s.blocks)?.text).toBe('færdig')
  })

  it('denseBlocks tåler tomt/kun-huller input', () => {
    expect(denseBlocks([])).toEqual([])
    expect(denseBlocks([undefined, null] as never)).toEqual([])
    expect(lastTextBlock([undefined, null] as never)).toBeUndefined()
  })
})
