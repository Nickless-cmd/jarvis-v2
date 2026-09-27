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

  // Bjørn 27/9-2026: «min besked under det billede jeg uploaded [bliver]
  // strippet». Serveren lægger brugerens tekst i `content` og KUN
  // attachment-blokkene i `content_json` — uden denne regel faldt teksten væk
  // i det øjeblik serveren overtog beskeden fra den optimistiske kopi.
  it('bevarer brugerens tekst når content_json kun bærer vedhæftningen', () => {
    const msg = {
      role: 'user',
      content: 'her er et test billede',
      content_json: [
        { type: 'image', attachment_id: 'abc123', filename: 'Skærmbillede.png', mime_type: 'image/png' },
      ],
    }
    const blocks = messageToBlocks(msg as any)
    expect(blocks[0]).toEqual({ type: 'text', text: 'her er et test billede' })
    expect(blocks.filter((b: any) => b.type === 'image')).toHaveLength(1)
  })

  it('sætter teksten FØRST — samme rækkefølge som den optimistiske kopi', () => {
    const msg = {
      role: 'user',
      content: 'to billeder',
      content_json: [
        { type: 'image', attachment_id: 'a' },
        { type: 'image', attachment_id: 'b' },
      ],
    }
    const blocks = messageToBlocks(msg as any)
    expect(blocks.map((b: any) => b.type)).toEqual(['text', 'image', 'image'])
  })

  it('dublerer IKKE teksten når content_json selv har en text-blok', () => {
    const msg = {
      role: 'assistant',
      content: 'svar',
      content_json: [
        { type: 'text', text: 'svar' },
        { type: 'tool_use', id: 'toolu_1', name: 'bash', input: {} },
      ],
    }
    const blocks = messageToBlocks(msg as any)
    expect(blocks.filter((b: any) => b.type === 'text')).toHaveLength(1)
  })

  it('tilføjer ingen tekst-blok når brugeren ikke skrev noget', () => {
    const msg = {
      role: 'user',
      content: '',
      content_json: [{ type: 'image', attachment_id: 'a' }],
    }
    const blocks = messageToBlocks(msg as any)
    expect(blocks.some((b: any) => b.type === 'text')).toBe(false)
    expect(blocks).toHaveLength(1)
  })
})
