import { render } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { MarkdownRenderer } from '../components/rich/MarkdownRenderer'
import { STANDARD_VARIANT, STREAMING_TEXT_VARIANTS, rehypeStreamingTextTail } from './streamingTextTail'

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

// ── Varianten skal faktisk kunne vælges (18/11-2026) ──────────────────────
//
// `STREAMING_TEXT_VARIANTS` bar fire navngivne sæt tal, men transformen læste
// hårdt `Normal`. Tre varianter var derfor tal ingen kunne bruge — en
// kapacitet der så ud som en kapacitet. Testen her går gennem transformen, så
// den måler de CSS-variabler der ender i DOM'en, ikke konstanten selv.

type HastNode = {
  type: string
  tagName?: string
  properties?: Record<string, unknown>
  value?: string
  children?: HastNode[]
}

function trae(tekst: string): HastNode {
  return {
    type: 'root',
    children: [
      { type: 'element', tagName: 'p', properties: {}, children: [{ type: 'text', value: tekst }] },
    ],
  }
}

function stilFor(variant?: 'Neutral' | 'Disabled' | 'Normal' | 'Snappy'): string {
  const t = trae('et to tre ')
  rehypeStreamingTextTail({ completedAtEnd: true, ...(variant ? { variant } : {}) })(t as never)
  const spans = (t.children?.[0]?.children ?? []) as HastNode[]
  const foerste = spans.find((n) => n.tagName === 'jarvis-stream-word')
  return String(foerste?.properties?.style ?? '')
}

describe('ordhalens variant', () => {
  it('bruger STANDARD_VARIANT naar ingen variant er angivet', () => {
    const standard = STREAMING_TEXT_VARIANTS[STANDARD_VARIANT]
    expect(stilFor()).toContain(`--streaming-tail-duration:${standard.duration}ms`)
  })

  it.each(['Neutral', 'Disabled', 'Normal', 'Snappy'] as const)(
    'sender %s-variantens egne tal til CSS',
    (variant) => {
      const p = STREAMING_TEXT_VARIANTS[variant]
      const stil = stilFor(variant)
      expect(stil).toContain(`--streaming-tail-duration:${p.duration}ms`)
      expect(stil).toContain(`--streaming-tail-color-delay:${p.colorDelay}ms`)
      expect(stil).toContain(`--streaming-tail-part-offset:${p.timeOffsetBetweenParts}ms`)
    },
  )

  it('giver fire forskellige varigheder — ingen variant er en kopi', () => {
    const varigheder = (['Neutral', 'Disabled', 'Normal', 'Snappy'] as const).map(
      (v) => STREAMING_TEXT_VARIANTS[v].duration,
    )
    expect(new Set(varigheder).size).toBe(4)
  })
})

describe('ordhalen genstarter animationen pr. ord', () => {
  it('monterer en FRISK span når et nyt ord indtager samme position (ellers ingen animationstart)', () => {
    const { container, rerender } = render(<MarkdownRenderer text="et to tre " streaming />)
    const foer = container.querySelector('.streaming-word-tail')
    expect(foer?.textContent).toBe('et ')
    rerender(<MarkdownRenderer text="et to tre fire " streaming />)
    const efter = container.querySelector('.streaming-word-tail')
    expect(efter?.textContent).toBe('to ')
    // Samme position, nyt ord: samme DOM-node ville genbruge en kørt animation.
    expect(efter).not.toBe(foer)
  })
})
