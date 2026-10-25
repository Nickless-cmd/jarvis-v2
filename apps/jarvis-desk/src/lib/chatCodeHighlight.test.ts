import { describe, expect, it, vi } from 'vitest'
import { getSingletonHighlighter } from 'shiki'
import { highlightChatCode, tokenizeChatCode } from './chatCodeHighlight'

/** shiki's `htmlStyle` er `string | Record<string, string>`. Fallback-grenen
 *  sætter altid et objekt; grammatik-grenen kan give en CSS-streng. */
const mork = (t: { htmlStyle?: string | Record<string, string> }) =>
  typeof t.htmlStyle === 'object' ? t.htmlStyle?.['--shiki-dark'] : undefined

describe('chat-kode highlighting', () => {
  it('tokeniserer kun nye linjer og bevarer syntaks på tværs af dem', async () => {
    const highlighter = await getSingletonHighlighter({ themes: ['github-light', 'github-dark'], langs: ['typescript'] })
    const spy = vi.spyOn(highlighter, 'codeToTokens')
    const first = tokenizeChatCode(highlighter, '/* kommentar\n', 'typescript', null)
    const next = tokenizeChatCode(highlighter, '/* kommentar\nfortsat */ const x = 1\n', 'typescript', first)
    expect(spy).toHaveBeenLastCalledWith('fortsat */ const x = 1\n', expect.objectContaining({ grammarState: first.grammarState }))
    const full = tokenizeChatCode(highlighter, next.code, 'typescript', null)
    const visible = (tokens: typeof next.tokens) => tokens.map((line) =>
      line.map((token) => [token.content, token.htmlStyle]))
    expect(visible(next.tokens)).toEqual(visible(full.tokens))
    spy.mockRestore()
  })

  it('farver en blok UDEN sprog-tag i stedet for at give rå tekst', async () => {
    // 24/10-2026: `if (!lang || !code) return` i ChatCodeBlock sendte 41 % af
    // alle kodeblokke (1.453 af 3.481) til ensfarvet rå tekst.
    const result = await highlightChatCode('const x = 1 // note', '', null)
    expect(result.lang).toBe('')
    expect(result.tokens.flat().length).toBeGreaterThan(1)
    const farver = new Set(result.tokens.flat().map(mork))
    expect(farver.size).toBeGreaterThan(1)
  })

  it('farver et sprog shiki ikke kender via fallback i stedet for at kaste', async () => {
    // `jarvis-ui` (34 blokke) findes ikke i bundlen. Før: `.catch(() => null)`
    // → rå tekst. Nu: scanneren farver den.
    const result = await highlightChatCode('{"type": "callout"}', 'jarvis-ui', null)
    expect(result.lang).toBe('jarvis-ui')
    expect(result.tokens.flat().length).toBeGreaterThan(0)
    const farver = new Set(result.tokens.flat().map(mork))
    expect(farver.size).toBeGreaterThan(0)
  })

  it('oversætter alias-sprog til en rigtig grammatik', async () => {
    // `cron` (95 blokke) og `shell` findes ikke, men `shellscript` gør.
    const result = await highlightChatCode('systemctl restart jarvis-api', 'cron', null)
    expect(result.lang).toBe('cron') // originalt navn bevares til sammenligning
    expect(result.tokens.flat().length).toBeGreaterThan(1)
  })

  it('bevarer det originale sprognavn så ChatCodeBlock kan matche det', async () => {
    // Fejlen der ellers opstår: tokenizeChatCode fik det OVERSATTE sprog, og
    // `highlighted.lang === lang` blev falsk → tilbage til rå tekst.
    const result = await highlightChatCode('echo hej', 'Shell', null)
    expect(result.lang).toBe('shell')
  })
})
