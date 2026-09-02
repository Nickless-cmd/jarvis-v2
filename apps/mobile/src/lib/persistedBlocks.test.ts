import { attachmentBlocks, hasOrdering, parseBlocks, thinkingBlock, threadBlocks } from './persistedBlocks'
import type { ChatMessage } from './types'

const msg = (over: Partial<ChatMessage> = {}): ChatMessage => ({
  id: 'm1',
  role: 'assistant',
  content: 'flad tekst',
  created_at: '2026-09-02T12:00:00Z',
  ...over
})

describe('parseBlocks', () => {
  it('læser serverens blokke', () => {
    const b = parseBlocks(msg({ content_json: '[{"type":"text","text":"hej"}]' }))
    expect(b).toHaveLength(1)
    expect(b?.[0]?.text).toBe('hej')
  })

  it('uden blokke: null, så vi falder tilbage på content', () => {
    expect(parseBlocks(msg())).toBeNull()
    expect(parseBlocks(msg({ content_json: '' }))).toBeNull()
    expect(parseBlocks(msg({ content_json: '   ' }))).toBeNull()
  })

  it('ugyldig JSON vælter ikke visningen', () => {
    expect(parseBlocks(msg({ content_json: '{ ikke json' }))).toBeNull()
    expect(parseBlocks(msg({ content_json: '{"type":"text"}' }))).toBeNull()
  })
})

describe('hasOrdering — bærer blokkene mere end content gør?', () => {
  it('ja når der både er værktøjer og tekst', () => {
    const b = parseBlocks(
      msg({ content_json: '[{"type":"text","text":"a"},{"type":"tool_use","name":"bash"}]' })
    )
    expect(hasOrdering(b)).toBe(true)
  })

  it('nej ved ren tekst — content siger det samme', () => {
    expect(hasOrdering(parseBlocks(msg({ content_json: '[{"type":"text","text":"a"}]' })))).toBe(false)
  })

  it('nej ved værktøjer uden tekst', () => {
    expect(hasOrdering(parseBlocks(msg({ content_json: '[{"type":"tool_use","name":"bash"}]' })))).toBe(false)
  })

  it('tom tekst tæller ikke', () => {
    const b = parseBlocks(
      msg({ content_json: '[{"type":"text","text":"   "},{"type":"tool_use","name":"bash"}]' })
    )
    expect(hasOrdering(b)).toBe(false)
  })
})

describe('threadBlocks', () => {
  it('progress-sporet hører ikke til i tråden', () => {
    const b = parseBlocks(
      msg({ content_json: '[{"type":"text","text":"a"},{"type":"progress"},{"type":"tool_use"}]' })
    )!
    expect(threadBlocks(b).map((x) => x.type)).toEqual(['text', 'tool_use'])
  })
})

describe('formen fra netværket er en påstand, ikke en garanti', () => {
  it('API\'et leverer et FÆRDIGPARSET array — ikke en streng', () => {
    // Denne antagelse væltede hele MessageList med
    // «undefined is not a function» fordi vi kaldte .trim() på et array.
    const b = parseBlocks(
      msg({ content_json: [{ type: 'text', text: 'hej' }] as unknown as string[] })
    )
    expect(b).toHaveLength(1)
    expect(b?.[0]?.text).toBe('hej')
  })

  it('en streng virker stadig', () => {
    expect(parseBlocks(msg({ content_json: '[{"type":"text","text":"a"}]' }))).toHaveLength(1)
  })

  it('uventede former giver null frem for at vælte visningen', () => {
    expect(parseBlocks(msg({ content_json: 42 as unknown as string }))).toBeNull()
    expect(parseBlocks(msg({ content_json: {} as unknown as string }))).toBeNull()
    expect(parseBlocks(msg({ content_json: [] as unknown as string[] }))).toBeNull()
  })
})

describe('taenkning og vedhaeftninger', () => {
  const msg = (blocks: unknown[]) =>
    ({ id: 'm', role: 'assistant', content: 'x', created_at: '', content_json: blocks } as never)

  it('finder taenke-blokken', () => {
    const b = parseBlocks(msg([{ type: 'thinking', seconds: 12, text: 'hm' }, { type: 'text', text: 'svar' }]))
    expect(thinkingBlock(b)?.seconds).toBe(12)
  })

  it('giver null naar der ikke blev taenkt', () => {
    expect(thinkingBlock(parseBlocks(msg([{ type: 'text', text: 'svar' }])))).toBeNull()
  })

  it('finder vedhaeftninger og bevarer raekkefoelgen', () => {
    const b = parseBlocks(msg([
      { type: 'image', attachment_id: 'a', filename: 'f.png' },
      { type: 'file', attachment_id: 'b', filename: 'x.zip' }
    ]))
    expect(attachmentBlocks(b).map((x) => x.attachment_id)).toEqual(['a', 'b'])
  })

  it('springer vedhaeftninger uden id over — en halv reference kan ikke hentes', () => {
    const b = parseBlocks(msg([{ type: 'image', filename: 'uden id' }, { type: 'image', attachment_id: '  ' }]))
    expect(attachmentBlocks(b)).toEqual([])
  })

  // De tre typer renderes af hver sin egen komponent OVER turen og maa ikke
  // ogsaa dukke op i den loebende blok-raekkefoelge.
  it('threadBlocks filtrerer taenkning, billeder og filer fra', () => {
    const b = parseBlocks(msg([
      { type: 'thinking', seconds: 3 },
      { type: 'image', attachment_id: 'a' },
      { type: 'file', attachment_id: 'b' },
      { type: 'progress', text: 'p' },
      { type: 'text', text: 'svar' }
    ]))!
    expect(threadBlocks(b).map((x) => x.type)).toEqual(['text'])
  })
})
