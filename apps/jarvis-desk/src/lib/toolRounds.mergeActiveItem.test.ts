import { describe, it, expect } from 'vitest'
import { groupToolRounds, mergeActiveItem, type RenderBlock, type ToolGroupBlock } from './toolRounds'
import type { ContentBlock } from './sseProtocol'

/**
 * `mergeActiveItem` — «forløbet skal ligne en tanke, ikke en log».
 *
 * Mønstret er hentet fra ChatGPT-mobil-appens `ReasoningActivitySequence`
 * (målt 14/11-2026): deres `mergeActiveItem` lægger en ny aktivitet IND i den
 * aktive række i stedet for at tilføje en ny. Vores `groupToolRounds` gjorde
 * det modsatte — enhver tekstblok afsluttede runden.
 *
 * Kæden er altid `groupToolRounds` → `mergeActiveItem`, så testene kører den
 * rigtige vej og ikke en kunstig mellemform.
 */

function tool(id: string, name = 'read_file', status: 'done' | 'error' | 'running' = 'done'): ContentBlock {
  return { type: 'tool_use', id, name, input: { path: `/f/${id}` }, status }
}
const text = (t: string): ContentBlock => ({ type: 'text', text: t })

const forloeb = (b: ContentBlock[]) =>
  mergeActiveItem(groupToolRounds(b as RenderBlock[]))

const grupper = (b: RenderBlock[]) => b.filter((x): x is ToolGroupBlock => x.type === 'tool_group')

describe('mergeActiveItem', () => {
  it('smelter to runder med kort mellemtekst til ÉN række', () => {
    const ud = forloeb([
      tool('a'), tool('b'),
      text('Nu ser jeg på resultatet.'),
      tool('c'),
    ])
    const g = grupper(ud)
    expect(g.length).toBe(1)
    expect(g[0]!.tools.map((t) => t.id)).toEqual(['a', 'b', 'c'])
  })

  it('bevarer rækkefølgen: kald og mellemtekst står som de kom', () => {
    const ud = forloeb([
      tool('a'),
      text('Først det her.'),
      tool('b'),
      text('Så det her.'),
      tool('c'),
    ])
    const g = grupper(ud)
    expect(g.length).toBe(1)
    expect(g[0]!.dele?.map((d) => (d.slags === 'kald' ? d.kald.id : d.tekst))).toEqual([
      'a', 'Først det her.', 'b', 'Så det her.', 'c',
    ])
  })

  it('en LANG mellemtekst bryder tanken — den er en replik, ikke en tankestemme', () => {
    const replik = 'x'.repeat(400)
    const ud = forloeb([tool('a'), text(replik), tool('b')])
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'text', 'tool_group'])
  })

  it('grænsen er præcis: 280 tegn smelter, 281 bryder', () => {
    const lige = forloeb([tool('a'), text('y'.repeat(280)), tool('b')])
    expect(grupper(lige).length).toBe(1)
    const over = forloeb([tool('a'), text('y'.repeat(281)), tool('b')])
    expect(grupper(over).length).toBe(2)
  })

  it('en FEJL bryder stadig ud og står alene — den må ikke forsvinde i «Kørte 3 ting»', () => {
    const ud = forloeb([tool('a'), tool('b', 'bash', 'error'), tool('c')])
    // Fejlen er en tool_use-blok uden gruppe, ikke en del af nogen `dele`.
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'tool_use', 'tool_group'])
    for (const g of grupper(ud)) {
      expect(g.tools.some((t) => t.status === 'error')).toBe(false)
    }
  })

  it('en anomali bryder også ud', () => {
    const ukendt = { ...tool('b'), anomali: 'uden-resultat' } as ContentBlock
    const ud = forloeb([tool('a'), ukendt, tool('c')])
    expect(ud.map((b) => b.type)).toEqual(['tool_group', 'tool_use', 'tool_group'])
  })

  it('kun mellemtekst bliver tekst — der er intet at folde', () => {
    const ud = mergeActiveItem([text('bare en sætning')] as RenderBlock[])
    expect(ud).toEqual([text('bare en sætning')])
  })

  it('tom ind → tom ud', () => {
    expect(mergeActiveItem([])).toEqual([])
  })

  it('uden mellemtekst er resultatet uændret fra groupToolRounds', () => {
    const blokke = [tool('a'), tool('b')] as RenderBlock[]
    const ud = mergeActiveItem(groupToolRounds(blokke))
    const g = grupper(ud)
    expect(g.length).toBe(1)
    expect(g[0]!.count).toBe(2)
    expect(g[0]!.tools.map((t) => t.id)).toEqual(['a', 'b'])
  })

  it('`count` tæller kald, ikke tekstdele', () => {
    const ud = forloeb([tool('a'), text('kort.'), tool('b'), text('også kort.'), tool('c')])
    expect(grupper(ud)[0]!.count).toBe(3)
  })
})
