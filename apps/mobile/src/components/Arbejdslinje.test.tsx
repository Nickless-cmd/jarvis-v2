import { act, render } from '@testing-library/react-native'
import { Arbejdslinje } from './Arbejdslinje'

/** Flad liste af testID'er og tekst i render-træets rækkefølge (oppefra og ned). */
const orden = (node: unknown, ud: string[] = []): string[] => {
  if (node == null) return ud
  if (typeof node === 'string') { ud.push(node); return ud }
  if (Array.isArray(node)) { for (const n of node) orden(n, ud); return ud }
  const n = node as { props?: { testID?: unknown }; children?: unknown }
  if (typeof n.props?.testID === 'string') ud.push(n.props.testID)
  orden(n.children, ud)
  return ud
}

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

  /**
   * Rækkefølgen er Bjørns (30/9-2026): animation → tokens → min/sec → det
   * linjen ellers viser. Tallene står FØR sætningen: de er det linjen melder
   * om arbejdet, sætningen er hvad den laver.
   */
  it('stiller tallene i Bjørns rækkefølge: puls, tokens, tid, sætning', async () => {
    jest.useFakeTimers()
    try {
      const s = await render(<Arbejdslinje tekst="Kører npm test" tokens={45200} />)
      await act(async () => { jest.advanceTimersByTime(3000) })
      const r = orden(s.toJSON())
      expect(r.indexOf('puls-ikon')).toBeLessThan(r.indexOf('arbejdslinje-tokens'))
      expect(r.indexOf('arbejdslinje-tokens')).toBeLessThan(r.indexOf('arbejdslinje-tid'))
      expect(r.indexOf('arbejdslinje-tid')).toBeLessThan(r.indexOf('Kører npm test'))
    } finally {
      jest.useRealTimers()
    }
  })

  it('viser token-tallet kort — «45.2k tokens», som desk', async () => {
    // Samme regel som desks liveness-linje, så de to klienter skriver tallet
    // ens. MUT: vis tallet råt → «45200 tokens» → fanger.
    const s = await render(<Arbejdslinje tekst="Kører npm test" tokens={45200} />)
    expect(s.getByText('45.2k tokens')).toBeTruthy()
  })

  it('skjuler token-tallet når der ikke er noget at vise', async () => {
    // Et nul er ikke et tal — det er en tur der lige er begyndt.
    // MUT: fjern `tokens > 0`-guarden → «0 tokens» står i linjen → fanger.
    const s = await render(<Arbejdslinje tekst="Kører npm test" tokens={0} />)
    expect(s.queryByTestId('arbejdslinje-tokens')).toBeNull()
  })

  it('uret vises først fra ét sekund — og taeller mens linjen staar der', async () => {
    // «0s» er ikke et tal. Uret hører til LINJEN og ikke til stream-tilstanden,
    // så det starter når linjen dukker op og forsvinder med den.
    // MUT: fjern `sek >= 1`-vægnet → «0s» staar i linjen → fanger.
    jest.useFakeTimers()
    try {
      const s = await render(<Arbejdslinje tekst="Kører npm test" />)
      expect(s.queryByTestId('arbejdslinje-tid')).toBeNull()
      await act(async () => { jest.advanceTimersByTime(3000) })
      expect(s.getByTestId('arbejdslinje-tid')).toBeTruthy()
      expect(s.getByText('3s')).toBeTruthy()
    } finally {
      jest.useRealTimers()
    }
  })
})
