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

  it('rækken har spørgsmålet som tilgængeligt navn', () => {
    // Rækken bærer ingen synlig tekst mere (4/10-2026) — uden aria-label ville
    // knappen stå uden navn for en skærmlæser.
    render(<Harness ids={['a', 'b']} />)
    expect(screen.getAllByRole('button')[0]!.getAttribute('aria-label')).toBe('besked a')
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

/* ── Kortet (4/10-2026, 1:1 med mockup'en) ─────────────────────────────────
 *
 * Historikken er to beslutninger der peger hver sin vej, og det er værd at
 * holde fast hvorfor den sidste vandt:
 *
 *  3/10: Bjørn — «panelet folder stadig ud, men kun med titler — svaret vises i
 *  et rent kort ved den linje musen er på». Panelet bar titlerne, kortet KUN
 *  svaret.
 *
 *  4/10: fem skærmbilleder og «1:1». Railen har INGEN tekst, og kortet bærer
 *  BEGGE: spørgsmålet i fed som første linje og svaret i op til tre dæmpede
 *  linjer under. Det er den ene linje der siger hvad rækken ER — derfor vises
 *  kortet også for en tur uden svar, hvor den gamle regel ryddede det helt.
 */
describe('MessageRail — kortet', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('panelet bærer INGEN tekst — kun streger', () => {
    render(<HarnessMedSvar ids={['a', 'b']} svar="det korte svar" />)
    expect(document.querySelector('.msg-rail-text')).toBeNull()
    expect(document.querySelector('.msg-rail-spm')).toBeNull()
    // Og kortet findes ikke, før musen er der.
    expect(document.querySelector('.msg-rail-kort')).toBeNull()
  })

  it('hover viser spørgsmål OG svar i kortet', () => {
    render(<HarnessMedSvar ids={['a', 'b']} svar="det korte svar" />)
    fireEvent.mouseEnter(screen.getAllByRole('button')[0]!)
    const kort = document.querySelector('.msg-rail-kort')!
    expect(kort.querySelector('.msg-rail-kort-spm')?.textContent).toBe('besked a')
    expect(kort.querySelector('.msg-rail-kort-svar')?.textContent).toBe('det korte svar')
  })

  it('en tur UDEN svar viser stadig spørgsmålet', () => {
    // 4/10: før ryddede et tomt svar kortet helt, og så stod rækken uden noget
    // at læse. Spørgsmålet findes altid — svaret gør ikke.
    render(<HarnessMedSvar ids={['a', 'b']} svar="" />)
    fireEvent.mouseEnter(screen.getAllByRole('button')[0]!)
    const kort = document.querySelector('.msg-rail-kort')
    expect(kort?.querySelector('.msg-rail-kort-spm')?.textContent).toBe('besked a')
    expect(kort?.querySelector('.msg-rail-kort-svar')).toBeNull()
  })

  it('kortet bærer et bogmærke-ikon — det er «saved» i navnet', () => {
    render(<HarnessMedSvar ids={['a', 'b']} svar="noget" />)
    fireEvent.mouseEnter(screen.getAllByRole('button')[0]!)
    expect(document.querySelector('.msg-rail-kort-ikon')).not.toBeNull()
  })

  it('en fejlet tur meldes med ORD i kortet, ikke med farve i railen', () => {
    // Bjørn 4/10-2026: «den røde farve i dit rail irriterer mig, væk med den».
    // Rødt blandt streger læste som en anden SLAGS punkt, ikke som «her gik det
    // galt» — spørgsmålet besvares i stedet hvor der er plads til ord.
    render(<HarnessMedSvar ids={['a', 'b']} svar="noget" fejl />)
    fireEvent.mouseEnter(screen.getAllByRole('button')[0]!)
    expect(document.querySelector('.msg-rail-kort-fejl')?.textContent).toContain('fejl')
  })

  it('en tur UDEN fejl melder ingenting', () => {
    render(<HarnessMedSvar ids={['a', 'b']} svar="noget" />)
    fireEvent.mouseEnter(screen.getAllByRole('button')[0]!)
    expect(document.querySelector('.msg-rail-kort-fejl')).toBeNull()
  })

  it('musen væk fra railen rydder kortet', () => {
    render(<HarnessMedSvar ids={['a', 'b']} svar="noget" />)
    fireEvent.mouseEnter(screen.getAllByRole('button')[0]!)
    expect(document.querySelector('.msg-rail-kort')).not.toBeNull()
    fireEvent.mouseLeave(screen.getByRole('navigation', { name: 'Spring til besked' }))
    expect(document.querySelector('.msg-rail-kort')).toBeNull()
  })
})

function HarnessMedSvar({ ids, svar, fejl }: { ids: string[]; svar: string; fejl?: boolean }) {
  const ref = useRef<HTMLDivElement>(null)
  return (
    <div ref={ref} style={{ position: 'relative' }}>
      <MessageRail
        containerRef={ref}
        anchors={ids.map((id) => ({ id, label: `besked ${id}`, svar: svar || undefined, fejl }))}
      />
      {ids.map((id) => <div key={id} data-rail-id={id}>m{id}</div>)}
    </div>
  )
}
