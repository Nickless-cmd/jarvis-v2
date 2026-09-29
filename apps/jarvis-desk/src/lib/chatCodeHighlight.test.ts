import { describe, expect, it, vi } from 'vitest'
import { getSingletonHighlighter } from 'shiki'
import { tokenizeChatCode } from './chatCodeHighlight'

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
})
