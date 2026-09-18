import { describe, it, expect } from 'vitest'
import { groupToolRounds, type RenderBlock, type ToolGroupBlock } from './toolRounds'
import type { ContentBlock } from './sseProtocol'

/**
 * Kontrakten ÆNDREDE sig 8/9-2026. Før foldede vi kun ≥3 sammenhængende
 * read/søge-kald og lod resten stå enkeltvis. Mobilen grupperer HELE runden
 * uanset værktøj — fortælling → én linje → fortælling — og Bjørn bad om 1:1.
 */

function tool(id: string, name = 'read_file', status: 'done' | 'error' | 'running' = 'done'): ContentBlock {
  return { type: 'tool_use', id, name, input: { path: `/f/${id}` }, status }
}
const text = (t: string): ContentBlock => ({ type: 'text', text: t })
const grupper = (b: ContentBlock[]) => groupToolRounds(b as RenderBlock[])

describe('groupToolRounds', () => {
  it('samler en hel runde til ÉN gruppe — også blandede værktøjer', () => {
    const ud = grupper([tool('a', 'read_file'), tool('b', 'bash'), tool('c', 'edit_file')])
    expect(ud.length).toBe(1)
    expect((ud[0] as ToolGroupBlock).count).toBe(3)
  })

  it('grupperer også et ENKELT kald — linjen er den samme uanset antal', () => {
    // Før stod ét kald som sit eget kort. Mobilen viser samme linje for ét som
    // for ti; kun teksten skifter.
    const ud = grupper([tool('a')])
    expect(ud.length).toBe(1)
    expect(ud[0]!.type).toBe('tool_group')
  })

  it('tekst afslutter runden', () => {
    const ud = grupper([tool('a'), tool('b'), text('mellemsvar'), tool('c')])
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'text', 'tool_group'])
    expect((ud[0] as ToolGroupBlock).count).toBe(2)
    expect((ud[2] as ToolGroupBlock).count).toBe(1)
  })

  it('en FEJL brydes ud og står alene', () => {
    // En fejl må aldrig forsvinde ind i «Kørte 5 værktøjer» — den er netop det
    // man leder efter.
    const ud = grupper([tool('a'), tool('b', 'bash', 'error'), tool('c')])
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'tool_use', 'tool_group'])
  })

  it('en anomali står også alene — den er lige så meget noget man leder efter', () => {
    const ukendt = { ...tool('b'), anomali: 'uden-resultat' } as ContentBlock
    const ud = grupper([tool('a'), ukendt, tool('c')])
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'tool_use', 'tool_group'])
  })

  // Hele kæden efter en genindlæsning: gemt blok → fold → gruppering. Før
  // gemte serveren alle udfald som «done», og en fejl blev foldet ind i
  // gruppen. Nu bærer den gemte blok status, og fejlen står alene.
  it('efter genindlæsning står en gemt fejl stadig alene', async () => {
    const { foldToolResults } = await import('./foldToolResults')
    const gemt = [
      { type: 'tool_use', id: 'a', name: 'read_file', input: {} },
      { type: 'tool_result', tool_use_id: 'a', status: 'done', content: 'ok', is_error: false },
      { type: 'tool_use', id: 'b', name: 'bash', input: {} },
      { type: 'tool_result', tool_use_id: 'b', status: 'error', content: 'exit 1', is_error: true },
      { type: 'tool_use', id: 'c', name: 'read_file', input: {} },
      { type: 'tool_result', tool_use_id: 'c', status: 'done', content: 'ok', is_error: false },
    ]
    const ud = grupper(foldToolResults(gemt as any))
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'tool_use', 'tool_group'])
    expect(ud[1]).toMatchObject({ id: 'b', status: 'error' })
  })

  it('lader tekst-only besked være helt urørt', () => {
    const ud = grupper([text('bare tekst')])
    expect(ud).toEqual([text('bare tekst')])
  })

  it('tom ind → tom ud', () => {
    expect(grupper([])).toEqual([])
  })
})
