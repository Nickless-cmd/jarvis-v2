import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useRef } from 'react'
import { MessageRail } from './MessageRail'

function Harness({ ids }: { ids: string[] }) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <MessageRail containerRef={ref} anchors={ids.map((id) => ({ id, label: `besked ${id}` }))} />
      {ids.map((id) => <div key={id} data-rail-id={id}>m{id}</div>)}
    </div>
  )
}

describe('MessageRail', () => {
  it('skjuler sig ved <2 ankre', () => {
    render(<Harness ids={['a']} />)
    expect(screen.queryByRole('navigation', { name: 'Spring til besked' })).not.toBeInTheDocument()
  })

  it('viser en række pr. anker (≥2) + klik scroller', () => {
    const scroll = vi.fn()
    Element.prototype.scrollIntoView = scroll
    render(<Harness ids={['a', 'b', 'c']} />)
    const rows = screen.getAllByRole('button')
    expect(rows.length).toBe(3)
    fireEvent.click(rows[1]!)
    expect(scroll).toHaveBeenCalled()
  })

  it('markerer det afsnit man STÅR I — ikke bare det sidste', () => {
    // Før var `is-active` hardkodet til det SIDSTE anker. Det fortalte ikke
    // hvor man var, men hvor samtalen sluttede — noget man i forvejen ved
    // (Bjørn 8/9-2026: «rimelig useriøst og ufunktionelt»).
    //
    // I jsdom er alle rects 0, så alle ankre tæller som «rullet forbi», og det
    // sidste vinder. Pointen testen holder på er at markeringen KOMMER fra
    // positionen — ikke fra en hardkodet indeks.
    render(<Harness ids={['a', 'b', 'c']} />)
    const rows = screen.getAllByRole('button')
    const aktive = rows.filter((r) => r.className.includes('is-active'))
    expect(aktive.length).toBe(1)
    expect(rows[2]!.getAttribute('aria-current')).toBe('true')
  })
})

/* ── Skinnen trækker sig i en smal rude (spec punkt 3.5, 29/9-2026) ─────────
 *
 * Skinnen folder ved hover op til 230 px tekst ud OVEN PÅ samtalen. I en smal
 * rude dækker den dermed det den skal hjælpe med at læse.
 *
 * Reglen selv er målt i `lib/railSynlighed.test.ts`. Den her måler noget
 * andet: at komponenten faktisk BRUGER den. En mutationskørsel fjernede
 * `if (!synlig) return null` og alle tests bestod — i jsdom er clientWidth 0,
 * så skinnen var synlig uanset. Derfor stilles bredden op eksplicit.
 */
function medBredde(clientWidth: number) {
  const ægte = window.getComputedStyle.bind(window)
  vi.spyOn(window, 'getComputedStyle').mockImplementation((el, pe) => {
    const s = ægte(el as Element, pe as string | undefined)
    if ((el as HTMLElement).dataset?.rolle === 'transcript') {
      return { ...s, paddingLeft: '24px', paddingRight: '24px' } as CSSStyleDeclaration
    }
    return s
  })
  return function Harness({ ids }: { ids: string[] }) {
    const ref = useRef<HTMLDivElement>(null)
    return (
      <div ref={(n) => {
        if (n) {
          n.dataset.rolle = 'transcript'
          Object.defineProperty(n, 'clientWidth', { value: clientWidth, configurable: true })
        }
        ;(ref as { current: HTMLDivElement | null }).current = n
      }} style={{ position: 'relative' }}>
        <MessageRail containerRef={ref} anchors={ids.map((id) => ({ id, label: `besked ${id}` }))} />
        {ids.map((id) => <div key={id} data-rail-id={id}>m{id}</div>)}
      </div>
    )
  }
}

describe('MessageRail — bredde', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('en BRED rude viser skinnen', () => {
    const H = medBredde(1200)          // 1200 - 48 = 1152 > 900
    render(<H ids={['a', 'b', 'c']} />)
    expect(screen.getByRole('navigation', { name: 'Spring til besked' })).toBeInTheDocument()
  })

  it('en SMAL rude skjuler den — også med ankre nok', () => {
    const H = medBredde(800)           // 800 - 48 = 752 ≤ 900
    render(<H ids={['a', 'b', 'c']} />)
    expect(screen.queryByRole('navigation', { name: 'Spring til besked' })).not.toBeInTheDocument()
  })

  it('grænsen går på transcriptets INDHOLDSbredde, ikke dens ydre', () => {
    // 940 ydre - 48 padding = 892 → under. Måltes der på det ydre tal, ville
    // den samme rude stå som 940 og blive vist. 48 px afgør sagen her.
    const H = medBredde(940)
    render(<H ids={['a', 'b', 'c']} />)
    expect(screen.queryByRole('navigation', { name: 'Spring til besked' })).not.toBeInTheDocument()
  })
})

/* ── Hvilende tilstand må ikke ændre sig (spec punkt 3.2) ───────────────────
 *
 * Svar-uddraget lever KUN i den udfoldede tilstand. Rækken er 10px i hvile, og
 * skinnen er 26px bred — det er den form Bjørn har tunet, og et preview må
 * ikke koste den. Testen findes fordi `align-items: flex-start` og en
 * `margin-top` på stregen blev sat i samme ombæring: gik de galt, ville
 * stregerne rykke sig i hvile uden at nogen test så det.
 */
describe('MessageRail — svar-uddraget', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('svaret står i sin egen linje under spørgsmålet', () => {
    render(
      <HarnessMedSvar ids={['a', 'b']} svar="det korte svar" />,
    )
    const spm = document.querySelector('.msg-rail-spm')
    const svar = document.querySelector('.msg-rail-svar')
    expect(spm?.textContent).toContain('besked a')
    expect(svar?.textContent).toBe('det korte svar')
    // Rækkefølgen betyder noget: spørgsmålet først.
    expect(spm).toBeTruthy(); expect(svar).toBeTruthy()
    expect(spm!.compareDocumentPosition(svar!) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
  })

  it('en tur UDEN svar får ingen tom linje', () => {
    // En tom `<span>` ville stadig tage plads og gøre rækken højere.
    render(<HarnessMedSvar ids={['a', 'b']} svar="" />)
    expect(document.querySelector('.msg-rail-svar')).toBeNull()
  })

  it('spørgsmålet står stadig i `title`, så det kan læses uklippet', () => {
    render(<HarnessMedSvar ids={['a', 'b']} svar="noget" />)
    const t = document.querySelector('.msg-rail-text')
    expect(t?.getAttribute('title')).toBe('besked a')
  })
})

function HarnessMedSvar({ ids, svar }: { ids: string[]; svar: string }) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <MessageRail
        containerRef={ref}
        anchors={ids.map((id) => ({ id, label: `besked ${id}`, svar: svar || undefined }))}
      />
      {ids.map((id) => <div key={id} data-rail-id={id}>m{id}</div>)}
    </div>
  )
}
