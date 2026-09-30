import { render } from '@testing-library/react-native'
import { Arbejdslinje } from './Arbejdslinje'

/**
 * `render` er ASYNKRON i dette bibliotek (samme mønster som
 * `InlineToolGroup.test.tsx` og `MessageList.test.tsx`), så hver test venter.
 */
describe('Arbejdslinje', () => {
  it('viser sætningen med puls og prikker', async () => {
    const s = await render(<Arbejdslinje tekst="Læser useChatScroll.ts" />)
    expect(s.getByTestId('arbejdslinje')).toBeTruthy()
    expect(s.getByText('Læser useChatScroll.ts')).toBeTruthy()
    expect(s.getByTestId('puls-ikon')).toBeTruthy()
    expect(s.getByTestId('prikker', { includeHiddenElements: true })).toBeTruthy()
  })

  /**
   * Mærket skal være det ANIMEREDE, ikke det statiske `PulsIkon`.
   *
   * Bjørn 30/9-2026: «dit/husets ikon mangler animation som i header». Det
   * statiske mærke tegnede sig som SVG (`<Rect fill=…>`), det animerede som
   * tre Views der skalerer (`backgroundColor` i stylen). Forskellen er
   * derfor målbar: en bjælke med `backgroundColor` findes KUN i den
   * animerede form.
   *
   * MUT: byt `AnimeretPuls` tilbage til `PulsIkon` → ingen bjælke med
   * `backgroundColor` → fanger.
   */
  it('mærket er det ANIMEREDE — ikke det statiske SVG-ikon', async () => {
    const s = await render(<Arbejdslinje tekst="Læser useChatScroll.ts" />)
    const ikon = s.getByTestId('puls-ikon')
    const flad = (stil: unknown): Record<string, unknown> =>
      Array.isArray(stil) ? Object.assign({}, ...stil.map(flad)) : ((stil ?? {}) as Record<string, unknown>)
    const medBaggrund: unknown[] = []
    const gaa = (node: unknown): void => {
      if (!node || typeof node !== 'object') return
      const n = node as { props?: { style?: unknown }; children?: unknown }
      if (n.props && typeof flad(n.props.style).backgroundColor === 'string') medBaggrund.push(n)
      const børn = n.children
      if (Array.isArray(børn)) børn.forEach(gaa)
      else if (børn) gaa(børn)
    }
    gaa(ikon)
    expect(medBaggrund.length).toBeGreaterThan(0)
  })

  it('tegner INTET når der ikke er noget at vise', async () => {
    // Hele pointen med «forsvinder når streamen slutter»: ingen tom bjælke.
    // MUT: fjern null-guarden → en bar linje står tilbage efter svaret → fanger.
    const s = await render(<Arbejdslinje tekst={null} />)
    expect(s.queryByTestId('arbejdslinje')).toBeNull()
    expect(s.queryByTestId('puls-ikon')).toBeNull()
  })

  it('bærer teksten som tilgængeligheds-label — ikke kun som pixels', async () => {
    const s = await render(<Arbejdslinje tekst="Kører npm test" />)
    expect(s.getByLabelText('Kører npm test')).toBeTruthy()
  })
})
