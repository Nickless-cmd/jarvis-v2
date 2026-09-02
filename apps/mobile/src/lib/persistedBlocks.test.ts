import { hasOrdering, parseBlocks, threadBlocks } from './persistedBlocks'
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

