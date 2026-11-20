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

  it('genbruger ordets DOM-node når nye ord kommer til — og giver det nye ord en frisk', () => {
    // MÅLT 20/11-2026 i Chromium: med kun tre wrappers rykkede hvert nyt ord
    // alle positioner (react-markdown nøgler `<tagName>-<antal>`), React
    // genmonterede dem, og hvert ord animerede op til TRE gange. Nu har hvert
    // afsluttet ord en stabil position, så noden overlever — og en overlevende
    // node starter ikke sin CSS-animation forfra. Selve starttallet er målt i
    // Chromium (`streamingTextTail.farve.maaling.test.ts`); jsdom har ingen
    // animationsmotor, så her måles nodens IDENTITET, som er årsagen.
    const { container, rerender } = render(<MarkdownRenderer text="Et to " streaming />)
    const ordNode = (t: string) => [...container.querySelectorAll('jarvis-stream-word, span')].find((n) => n.textContent?.trim() === t)
    const et = ordNode('Et')
    const to = ordNode('to')
    expect(et?.classList.contains('streaming-word-tail')).toBe(true)

    rerender(<MarkdownRenderer text="Et to tre " streaming />)
    expect(ordNode('Et')).toBe(et)
    expect(ordNode('to')).toBe(to)
    const tre = ordNode('tre')
    expect(tre).toBeTruthy()
    expect(tre?.classList.contains('streaming-word-tail')).toBe(true)

    rerender(<MarkdownRenderer text="Et to tre fire " streaming />)
    // «Et» har forladt de sidste tre — men beholder sin klasse (animationen må ikke kappes)
    // og sin node.
    expect(ordNode('Et')).toBe(et)
    expect(ordNode('tre')).toBe(tre)
    expect(ordNode('fire')).not.toBe(tre)
  })

  it('et enkelt nyt ord starter straks (order 0) — ikke efter 2× forskydningen', async () => {
    const { container, rerender } = render(<MarkdownRenderer text="et to tre " streaming />)
    await Promise.resolve() // batchen er per commit; næste commit er et nyt batch
    rerender(<MarkdownRenderer text="et to tre fire " streaming />)
    const fire = [...container.querySelectorAll('.streaming-word-tail')].find((n) => n.textContent?.trim() === 'fire') as HTMLElement
    expect(fire.style.getPropertyValue('--streaming-tail-order')).toBe('0')
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

  it('Snappy er baseline og bærer GPT-appens egne tal', () => {
    expect(STANDARD_VARIANT).toBe('Snappy')
    // Laest ud af /opt/codex-desktop/resources/app.asar, DILStreamingText: `c`.
    expect(STREAMING_TEXT_VARIANTS.Snappy).toMatchObject({
      duration: 220,
      colorDelay: 99,
      timeOffsetBetweenParts: 30,
    })
  })
})
