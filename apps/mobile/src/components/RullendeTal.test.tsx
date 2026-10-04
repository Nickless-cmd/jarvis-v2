import { render } from '@testing-library/react-native'
import { CIF_HOEJDE, RullendeTokens, RullendeUr } from './RullendeTal'

/**
 * Hjulenes lodrette position i px, i træets rækkefølge (venstre → højre).
 *
 * Et hjul viser cifferet ved `-position / CIF_HOEJDE`, så positionen er det
 * eneste sted i træet hvor man kan se HVILKET ciffer der faktisk står — og
 * dermed om et hjul blev GENBRUGT (står på det gamle ciffer) eller
 * nymonteret (står på sit eget). Det er den forskel testen nedenfor hviler på.
 */
const hjuL = (s: { root: unknown }): number[] => {
  const ud: number[] = []
  const gaa = (n: unknown): void => {
    if (!n || typeof n !== 'object') return
    if (Array.isArray(n)) {
      for (const x of n) gaa(x)
      return
    }
    const node = n as { props?: { style?: unknown }; children?: unknown }
    const st = node.props?.style
    if (st && typeof st === 'object' && !Array.isArray(st)) {
      const t = (st as { transform?: unknown }).transform
      if (Array.isArray(t)) {
        for (const d of t) {
          const ty = (d as { translateY?: unknown } | null)?.translateY
          if (ty !== undefined && Number.isFinite(Number(ty))) ud.push(Number(ty))
        }
      }
    }
    if (Array.isArray(node.children)) for (const c of node.children) gaa(c)
  }
  gaa(s.root)
  return ud
}

/**
 * De rullende hjul i mobilens arbejdslinje (Bjørn 4/10-2026).
 *
 * Testene her ser det et stillbillede IKKE kan: at hvert ciffer faktisk er et
 * HJUL med hele sin stribe — ikke bare et tegn der skiftes ud. Det er den
 * forskel der gør rullingen mulig, og den er målbar i træet.
 */
describe('RullendeTal', () => {
  /**
   * Bjørn 4/10-2026: «Den skal tælle Xs så XXs og så Xm og Xs». Under ét
   * minut vises kun sekunderne («3s») — ikke et foranstillet «00:» der står
   * og fylder uden at tælle.
   *
   * MUT: brug `MM:SS`-formatet → «00:03» → fanger.
   */
  it('under ét minut viser uret «3s» — ikke «00:03»', async () => {
    const s = await render(<RullendeUr sek={3} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('3s')).toBeTruthy()
  })

  it('to cifre sekunder — «45s»', async () => {
    const s = await render(<RullendeUr sek={45} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('45s')).toBeTruthy()
  })

  it('minuttet skrives «1m 12s» — ikke «01:12»', async () => {
    const s = await render(<RullendeUr sek={72} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('1m 12s')).toBeTruthy()
  })

  /**
   * Et hjul bærer hele sin stribe plus en dublet-0 at rulle ind i. Det er
   * dubletten der gør at 9 → 0 kan rulle FORLÆNS i stedet for at springe
   * baglæns gennem 8-7-6.
   *
   * «1m 12s» = tre ciffer-hjul (1, 1, 2). Hvert bærer '0' to gange: den
   * ægte 0 og dubletten.
   *
   * MUT: fjern dubletten (`i < cyklus` i stedet for `i <= cyklus`) → '0'
   * findes tre gange i stedet for seks → fanger.
   */
  it('hvert hjul bærer hele striben PLUS en dublet-0', async () => {
    const s = await render(<RullendeUr sek={72} farve="#fff" tegnFarve="#888" />)
    expect(s.getAllByText('0')).toHaveLength(6)
  })

  it('token-tallet er kort — «45.2k»', async () => {
    const s = await render(<RullendeTokens tokens={45200} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('45.2k')).toBeTruthy()
  })

  it('viser rå tal under 1000', async () => {
    const s = await render(<RullendeTokens tokens={456} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('456')).toBeTruthy()
  })

  it('ikke-cifre (punktum og k) står som tegn — ikke som hjul', async () => {
    // De skal stå stille. Er de hjul, ruller de med, og tallet bliver læsbart
    // forkert. MUT: rul dem som cifre → teksten findes ikke som selvstændig
    // Text-knude → fanger.
    const s = await render(<RullendeTokens tokens={45200} farve="#fff" tegnFarve="#888" />)
    expect(s.getByText('.')).toBeTruthy()
    expect(s.getByText('k')).toBeTruthy()
  })

  /**
   * MÅLT 4/10-2026: med `key={i}` genbrugte React det forreste hjul da
   * strengen voksede, så «9s» → «10s» lod hjul 0 gå 9 → 1. Da 1 < 9 ramte
   * det viklings-grenen og viste «0» — uret stod på «90s», og ved
   * «59s» → «1m 0s» stod det på «0m 0s».
   *
   * Nøglen er derfor afstanden FRA HØJRE (se `Ruller`). Her måles det
   * direkte i træet: det nye tier-hjul foran skal monteres på sit EGET
   * ciffer (1), ikke arve det gamle hjuls 9.
   *
   * MUT: sæt nøglen tilbage til `i` → det forreste hjul står på -144 (9)
   * i stedet for -16 (1) → fanger.
   */
  it('«9s» → «10s»: det nye ciffer foran monteres på sit eget tal', async () => {
    const s = await render(<RullendeUr sek={9} farve="#fff" tegnFarve="#888" />)
    expect(hjuL(s)).toEqual([-CIF_HOEJDE * 9])

    await s.rerender(<RullendeUr sek={10} farve="#fff" tegnFarve="#888" />)
    expect(hjuL(s)[0]).toBe(-CIF_HOEJDE * 1)
  })

})
