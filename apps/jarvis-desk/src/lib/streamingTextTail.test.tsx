import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarkdownRenderer } from '../components/rich/MarkdownRenderer'

describe('ordhalen i streamet Desk-markdown', () => {
  it.each([
    ['Et ', 1],
    ['Et to ', 2],
    ['Et to tre ', 3],
    ['Et to tre fire fem ', 3],
  ])('animerer kun de sidste 1-3 afsluttede ord i %j', (text, expected) => {
    const { container } = render(<MarkdownRenderer text={text} streaming />)

    const animated = [...container.querySelectorAll('.streaming-word-tail')]
    expect(animated).toHaveLength(expected)
    expect(animated.map((node) => node.textContent?.trim())).toEqual(
      text.trim().split(/\s+/).slice(-expected),
    )
  })

  it('lægger halen efter afsluttet-grænsen, ikke efter alle viste tegn', () => {
    const { container } = render(
      <MarkdownRenderer text="nul en to tre fire halv" streaming />,
    )

    const animated = [...container.querySelectorAll('.streaming-word-tail')]
    expect(animated.map((node) => node.textContent?.trim())).toEqual(['to', 'tre', 'fire'])
    expect(container.querySelector('p')?.textContent).toBe('nul en to tre fire halv')
    expect(animated.some((node) => node.textContent?.includes('halv'))).toBe(false)
  })

  it('animerer ikke en færdig eller historisk besked', () => {
    const { container } = render(
      <MarkdownRenderer text="Et færdigt svar" streaming={false} />,
    )

    expect(container.querySelectorAll('.streaming-word-tail')).toHaveLength(0)
  })

  it('genmonterer halen når et nyt ord bliver afsluttet — så CSS-animationen starter forfra', () => {
    // MÅLT 18/11-2026 i Chromium: et JS-lag (`element.animate()`) oven på
    // CSS-animationen gav TO animationer på samme element, der begge skrev
    // `opacity` og `color`. CSS'en er nu den eneste kilde. Genstarten per ord
    // bæres i stedet af `key`: skifter `data-stream-part-key`, afmonterer React
    // den gamle span og monterer en frisk — og en frisk CSS-animation starter
    // forfra. Denne test måler netop dét, ikke hvem der kalder `animate()`.
    const { container, rerender } = render(<MarkdownRenderer text="Et to " streaming />)
    const foer = [...container.querySelectorAll('.streaming-word-tail')]
    const foerNoegler = foer.map((node) => node.getAttribute('data-stream-part-key'))
    expect(foer).toHaveLength(2)

    rerender(<MarkdownRenderer text="Et to tre " streaming />)

    const efter = [...container.querySelectorAll('.streaming-word-tail')]
    expect(efter).toHaveLength(3)
    const efterNoegler = efter.map((node) => node.getAttribute('data-stream-part-key'))
    // Hvert ord bærer sin egen nøgle — derfor er ingen af de gamle spans genbrugt
    // til et nyt ord, og hver ny span får sin egen animation fra CSS.
    expect(new Set(efterNoegler).size).toBe(3)
    expect(efterNoegler).not.toEqual(foerNoegler)
    // At der ikke ligger JS-animationer oven på CSS'en kan ikke måles her:
    // jsdom har ingen `getAnimations()`. Det er målt i Chromium i stedet —
    // se `streamingTextTail.layout.maaling.test.ts`, hvor `getAnimations()`
    // giver præcis to CSS-drevne animationer og nul JS-drevne.
  })
})
