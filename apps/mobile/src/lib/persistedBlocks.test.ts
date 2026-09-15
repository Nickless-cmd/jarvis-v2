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

  it('springer vedhaeftninger uden nogen reference over — en halv reference kan ikke hentes', () => {
    const b = parseBlocks(msg([{ type: 'image', filename: 'uden id' }, { type: 'image', attachment_id: '  ' }]))
    expect(attachmentBlocks(b)).toEqual([])
  })

  // Målt 15/9-2026: Jarvis udgav et regneark med `publish_file`. Blokken lå i
  // beskeden med `url` og `kilde: "published"` — og INTET attachment_id. Det
  // gamle filter krævede et id, så filen faldt ud her og nåede aldrig skærmen,
  // selv om MessageAttachments hele tiden kunne vise den.
  it('en UDGIVET fil baerer sin egen url — den skal med', () => {
    const b = parseBlocks(msg([
      { type: 'file', filename: 'forbrug.xlsx', url: 'https://api.srvlab.dk/files/forbrug.xlsx', kilde: 'published' }
    ]))
    const fundet = attachmentBlocks(b)
    expect(fundet).toHaveLength(1)
    expect(fundet[0]?.url).toBe('https://api.srvlab.dk/files/forbrug.xlsx')
  })

  it('baade id- og url-baserede referencer kommer med, i raekkefoelge', () => {
    const b = parseBlocks(msg([
      { type: 'image', attachment_id: 'a', filename: 'a.png' },
      { type: 'file', filename: 'udgivet.xlsx', url: 'https://x/files/udgivet.xlsx', kilde: 'published' },
      { type: 'file', attachment_id: 'c', filename: 'c.zip' }
    ]))
    expect(attachmentBlocks(b).map((x) => x.attachment_id ?? x.url))
      .toEqual(['a', 'https://x/files/udgivet.xlsx', 'c'])
  })

  // Billeder og filer renderes over boblen; progress er sit eget flade spor.
  it('threadBlocks filtrerer billeder, filer og progress fra', () => {
    const b = parseBlocks(msg([
      { type: 'image', attachment_id: 'a' },
      { type: 'file', attachment_id: 'b' },
      { type: 'progress', text: 'p' },
      { type: 'text', text: 'svar' }
    ]))!
    expect(threadBlocks(b).map((x) => x.type)).toEqual(['text'])
  })

  // Taenkningen blev FOER filtreret fra her, fordi designet var «én foldet
  // linje over turen». Det holdt kun saa laenge en tur taenkte én gang. Jarvis
  // taenker mellem hvert vaerktoejskald, og resultatet var at kun den FOERSTE
  // overlevede — `thinkingBlock` tager `.find()`, resten faldt bort her.
  it('threadBlocks beholder ALLE tanker, i raekkefoelge', () => {
    const b = parseBlocks(msg([
      { type: 'thinking', text: 'foerste', seconds: 3 },
      { type: 'tool_use', name: 'bash', input: {} },
      { type: 'thinking', text: 'anden', seconds: 9 },
      { type: 'text', text: 'svar' }
    ]))!
    expect(threadBlocks(b).map((x) => x.type))
      .toEqual(['thinking', 'tool_use', 'thinking', 'text'])
  })
})
