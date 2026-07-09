import { describe, it, expect } from 'vitest'
import { stringToBlocks, messageToBlocks } from './normalizeMessage'

describe('stringToBlocks', () => {
  it('wraps a markdown string in one text block', () => {
    expect(stringToBlocks('**hej**')).toEqual([{ type: 'text', text: '**hej**' }])
  })
  it('empty string → empty array', () => {
    expect(stringToBlocks('')).toEqual([])
  })
})

describe('messageToBlocks', () => {
  it('bruger content_json (foldet) når til stede', () => {
    const msg = { role: 'assistant', content: 'svar', content_json: [
      { type: 'text', text: 'svar' },
      { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} },
      { type: 'tool_result', tool_use_id: 'toolu_1', status: 'done', content: 'ok' },
    ] }
    const blocks = messageToBlocks(msg as any)
    const tu = blocks.find((b: any) => b.type === 'tool_use') as any
    expect(tu.result).toBe('ok')
  })
  it('falder tilbage til stringToBlocks uden content_json', () => {
    const blocks = messageToBlocks({ role: 'assistant', content: 'ren tekst' } as any)
    expect(blocks).toEqual([{ type: 'text', text: 'ren tekst' }])
  })
})
