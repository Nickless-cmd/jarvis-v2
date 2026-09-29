import { describe, it, expect, vi, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { EditedFilesCard } from './EditedFilesCard'

const FILER = [{ path: 'apps/x/ChangesPanel.tsx', gange: 1 }, { path: 'apps/x/ChangesPanel.test.tsx', gange: 1 }]

describe('EditedFilesCard', () => {
  it('siger hvor mange filer — og viser dem', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} />)
    expect(screen.getByText('Redigerede 2 filer')).toBeInTheDocument()
    expect(screen.getByText('x/ChangesPanel.tsx')).toBeInTheDocument()
  })

  it('bøjer ental rigtigt', () => {
    render(<EditedFilesCard filer={[FILER[0]!]} onAabn={() => {}} />)
    expect(screen.getByText('Redigerede 1 fil')).toBeInTheDocument()
  })

  it('viser INTET når der ikke er redigeret noget', () => {
    const { container } = render(<EditedFilesCard filer={[]} onAabn={() => {}} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('klik på en fil åbner NETOP den fil', () => {
    const aabn = vi.fn()
    render(<EditedFilesCard filer={FILER} onAabn={aabn} />)
    fireEvent.click(screen.getByText('x/ChangesPanel.test.tsx'))
    expect(aabn).toHaveBeenCalledWith('apps/x/ChangesPanel.test.tsx')
  })

  it('«Vis ændringer» åbner ruden på den første fil', () => {
    const aabn = vi.fn()
    render(<EditedFilesCard filer={FILER} onAabn={aabn} />)
    fireEvent.click(screen.getByRole('button', { name: 'Vis ændringer' }))
    expect(aabn).toHaveBeenCalledWith('apps/x/ChangesPanel.tsx')
  })

  it('tallene vises når de KENDES', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}}
      tal={{ 'apps/x/ChangesPanel.tsx': { added: 166, removed: 0 } }} />)
    expect(screen.getByText('+166')).toBeInTheDocument()
  })

  it('en fil UDEN kendte tal får ikke «+0 −0»', () => {
    // Tallene kommer fra værktøjets resultat. Mangler de, ville 0 være et gæt.
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} tal={{}} />)
    expect(screen.queryByText('+0')).not.toBeInTheDocument()
  })

  it('en fil rettet flere gange er ÉN række — men antallet siges', () => {
    render(<EditedFilesCard filer={[{ path: 'a.ts', gange: 3 }]} onAabn={() => {}} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(1)
    expect(screen.getByText('3×')).toBeInTheDocument()
  })

  it('viser tre filer først og kan folde resten ud', () => {
    const filer = Array.from({ length: 5 }, (_, i) => ({ path: `src/fil-${i}.ts`, gange: 1 }))
    render(<EditedFilesCard filer={filer} onAabn={() => {}} />)
    expect(screen.getAllByRole('listitem')).toHaveLength(3)
    fireEvent.click(screen.getByRole('button', { name: 'Vis 2 filer mere' }))
    expect(screen.getAllByRole('listitem')).toHaveLength(5)
  })

  it('summerer kun kendte per-fil-tal i overskriften', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} tal={{
      'apps/x/ChangesPanel.tsx': { added: 9, removed: 4 },
      'apps/x/ChangesPanel.test.tsx': { added: 3, removed: 1 },
    }} />)
    expect(document.querySelector('.edited-files-head')).toHaveTextContent('+12')
    expect(document.querySelector('.edited-files-head')).toHaveTextContent('−5')
  })

  it('beder om bekræftelse før fortryd og viser kvittering', async () => {
    const onFortryd = vi.fn().mockResolvedValue({ status: 'ok', files: 2 })
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} onFortryd={onFortryd} />)
    fireEvent.click(screen.getByRole('button', { name: 'Fortryd' }))
    expect(onFortryd).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Ja, fortryd 2 filer' }))
    await waitFor(() => expect(onFortryd).toHaveBeenCalledOnce())
    expect(await screen.findByText('2 filer fortrudt')).toBeInTheDocument()
  })

  it('viser konflikt uden at kalde ændringen for fortrudt', async () => {
    const onFortryd = vi.fn().mockResolvedValue({ status: 'conflict', error: 'Filen er ændret siden.' })
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} onFortryd={onFortryd} />)
    fireEvent.click(screen.getByRole('button', { name: 'Fortryd' }))
    fireEvent.click(screen.getByRole('button', { name: 'Ja, fortryd 2 filer' }))
    expect(await screen.findByText('Filen er ændret siden.')).toBeInTheDocument()
  })

  // ── Hover-diff (Bjørn 29/9-2026: «en diff visning med scrool») ──────────
  it('viser diffen naar man holder musen over filnavnet', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}}
      diffs={{ 'apps/x/ChangesPanel.tsx': [{ gammel: 'gammel linje', ny: 'ny linje' }] }} />)
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
    fireEvent.mouseEnter(screen.getByText('x/ChangesPanel.tsx'))
    const tip = screen.getByRole('tooltip')
    expect(tip).toHaveTextContent('gammel linje')
    expect(tip).toHaveTextContent('ny linje')
  })

  it('viser ingen popup for en fil uden par', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}} diffs={{}} />)
    fireEvent.mouseEnter(screen.getByText('x/ChangesPanel.tsx'))
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })

  it('viser hver redigering af samme fil i raekkefoelge', () => {
    render(<EditedFilesCard filer={[{ path: 'a.ts', gange: 2 }]} onAabn={() => {}}
      diffs={{ 'a.ts': [{ gammel: 'v1', ny: 'v2' }, { gammel: 'v2', ny: 'v3' }] }} />)
    fireEvent.mouseEnter(screen.getByText('a.ts'))
    const tip = screen.getByRole('tooltip')
    expect(tip).toHaveTextContent('2 ændringer')
    expect(tip).toHaveTextContent('Ændring 1 af 2')
    expect(tip).toHaveTextContent('Ændring 2 af 2')
  })

  it('Escape lukker diffen igen', () => {
    render(<EditedFilesCard filer={FILER} onAabn={() => {}}
      diffs={{ 'apps/x/ChangesPanel.tsx': [{ gammel: 'a', ny: 'b' }] }} />)
    fireEvent.mouseEnter(screen.getByText('x/ChangesPanel.tsx'))
    expect(screen.getByRole('tooltip')).toBeInTheDocument()
    fireEvent.keyDown(window, { key: 'Escape' })
    expect(screen.queryByRole('tooltip')).not.toBeInTheDocument()
  })
})

/* ── Popup'en holder sig inde i chat-fladen (Bjoern 29/9-2026) ──────────────
 *
 * «den ska til den anden side altsaa over chatview.. og opad eller nedad
 * afhaengig af skaermen». Placeringen selv er maalt i
 * `lib/diffPopupPlacering.test.ts`. Den her beviser noget andet og lige saa
 * vigtigt: at KOMPONENTEN faktisk giver den chat-fladens kant og ikke
 * vinduets. En perfekt funktion som ingen kalder rigtigt er stadig fejlen. */

/** Giv `.main` og fil-raekken hver sit rektangel — jsdom giver ellers nul. */
function medFlader(raekke: { left: number; right: number; top: number; bottom: number }) {
  const r = (k: { left: number; right: number; top: number; bottom: number }) =>
    ({ ...k, width: k.right - k.left, height: k.bottom - k.top,
       x: k.left, y: k.top, toJSON: () => ({}) }) as DOMRect
  vi.spyOn(Element.prototype, 'getBoundingClientRect').mockImplementation(function (this: Element) {
    if ((this as HTMLElement).classList?.contains('main')) {
      return r({ left: 260, right: 1400, top: 0, bottom: 900 })
    }
    return r(raekke)
  })
  Object.defineProperty(window, 'innerWidth', { value: 1400, configurable: true })
  Object.defineProperty(window, 'innerHeight', { value: 900, configurable: true })
}

const iChatten = (tip: HTMLElement) => {
  const left = Number(tip.style.left.replace('px', ''))
  const bredde = Number(tip.style.width.replace('px', ''))
  return { left, hoejre: left + bredde }
}

describe('hover-diffens placering i panelet', () => {
  afterEach(() => { vi.restoreAllMocks() })

  it('lander ALDRIG over sidepanelet — heller ikke uden plads til hoejre', () => {
    // Hans sag: fil-raekken staar yderst til hoejre i en bred besked.
    medFlader({ left: 300, right: 1380, top: 300, bottom: 320 })
    render(
      <main className="main">
        <EditedFilesCard filer={FILER} onAabn={() => {}}
          diffs={{ 'apps/x/ChangesPanel.tsx': [{ gammel: 'a', ny: 'b' }] }} />
      </main>,
    )
    fireEvent.mouseEnter(screen.getByText('x/ChangesPanel.tsx'))
    const { left, hoejre } = iChatten(screen.getByRole('tooltip'))
    expect(left, 'popup\'en stikker ind over sidepanelet').toBeGreaterThanOrEqual(260)
    expect(hoejre).toBeLessThanOrEqual(1400)
  })

  it('en raekke naer skaermens bund vender popup\'en OPAD', () => {
    medFlader({ left: 300, right: 500, top: 850, bottom: 870 })
    render(
      <main className="main">
        <EditedFilesCard filer={FILER} onAabn={() => {}}
          diffs={{ 'apps/x/ChangesPanel.tsx': [{ gammel: 'a', ny: 'b' }] }} />
      </main>,
    )
    fireEvent.mouseEnter(screen.getByText('x/ChangesPanel.tsx'))
    const tip = screen.getByRole('tooltip')
    const top = Number(tip.style.top.replace('px', ''))
    const hoejde = Number(tip.style.maxHeight.replace('px', ''))
    expect(top).toBeLessThan(850)               // den aabner opad
    expect(top + hoejde).toBeLessThanOrEqual(900 - 8)
  })
})

describe('hover-diffens scrollbar', () => {
  // «scrollbar er synlig» (Bjoern 29/9-2026): systemets egen, bred og lys
  // midt i et moerkt felt. jsdom tegner ingen scrollbar, saa reglen laeses
  // fra kilden — men BEGGE motorer skal med, ellers staar den stadig i den
  // ene. En mutationskoersel fandt at dette hul var helt utestet.
  const css = () =>
    readFileSync(join(__dirname, '../../styles/app.css'), 'utf8')
      .replace(/\/\*[\s\S]*?\*\//g, '')

  it('Firefox: tynd og i temaets farver', () => {
    const krop = /\.edited-files-diff-krop[^{]*\{([^}]*)\}/g
    const blokke = [...css().matchAll(krop)].map((m) => m[1] ?? '').join(' ')
    expect(blokke).toMatch(/scrollbar-width\s*:\s*thin/)
    expect(blokke).toMatch(/scrollbar-color\s*:\s*var\(--line\)/)
  })

  it('Webkit: smal bane og en toemme i temaets farve', () => {
    const c = css()
    expect(c, 'ingen webkit-scrollbar-regel').toMatch(
      /\.edited-files-diff-krop[^{]*::-webkit-scrollbar[^-][^{]*\{[^}]*width\s*:\s*8px/)
    expect(c).toMatch(
      /\.edited-files-diff-krop[^{]*::-webkit-scrollbar-thumb[^{]*\{[^}]*background\s*:\s*var\(--line\)/)
  })

  it('ogsaa diffens EGEN vandrette scrollbar — den er et barn, ikke kroppen', () => {
    // DiffView scroller vandret inde i kroppen. Uden `*`-reglen stod netop
    // den tilbage som systemets egen.
    expect(css()).toMatch(/\.edited-files-diff-krop \*[^{]*\{[^}]*scrollbar-width\s*:\s*thin/)
  })
})
