import { render } from '@testing-library/react-native'
import { RullendeTokens, RullendeUr } from './RullendeTal'

/**
 * De rullende hjul i mobilens arbejdslinje (Bjørn 4/10-2026).
 *
 * Testene her ser det et stillbillede IKKE kan: at hvert ciffer faktisk er et
 * HJUL med hele sin stribe — ikke bare et tegn der skiftes ud. Det er den
 * forskel der gør rullingen mulig, og den er målbar i træet.
 */
describe('RullendeTal', () => {
  /**
   * Bjørn 4/10-2026: «Min skal først dukke op når den faktisk tæller.» Under
   * ét minut vises derfor kun sekunderne — ikke et «00:» der står og fylder
   * uden at tælle.
   *
   * MUT: sæt `MINUT_FRA_SEK` til 0 → «00:03» → fanger.
   */
  it('uret skjuler minuttet indtil det tæller — «03», ikke «00:03»', async () => {
    const s = await render(<RullendeUr sek={3} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('03')).toBeTruthy()
  })

  it('minuttet dukker op når det begynder at tælle — «59» → «01:00»', async () => {
    // Grænsen er selve pointen: 59 er stadig sekunder, 60 har et minut.
    const sidste = await render(<RullendeUr sek={59} farve="#fff" tegnFarve="#888" />)
    expect(sidste.getByLabelText('59')).toBeTruthy()
    const foerste = await render(<RullendeUr sek={60} farve="#fff" tegnFarve="#888" />)
    expect(foerste.getByLabelText('01:00')).toBeTruthy()
  })

  it('uret tæller minutter med — «01:12»', async () => {
    const s = await render(<RullendeUr sek={72} farve="#fff" tegnFarve="#888" />)
    expect(s.getByLabelText('01:12')).toBeTruthy()
  })

  /**
   * Sek-tiere har cyklus 6 (0-5), så 59 → 00 ruller rigtigt i stedet for at
   * vise et 6-tal undervejs. Det kan ses på hjulenes indhold: de tre
   * 10-cyklusser (min-tiere, min-enere, sek-enere) bærer hver en '9', mens
   * sek-tiere-hjulet ikke gør.
   *
   * MUT: giv alle hjul cyklus 10 → '9' findes fire gange i stedet for tre.
   */
  it('sek-tiere har cyklus 6 — der findes ingen 9 på det hjul', async () => {
    const s = await render(<RullendeUr sek={72} farve="#fff" tegnFarve="#888" />)
    expect(s.getAllByText('9')).toHaveLength(3)
  })

  /**
   * Et hjul bærer hele sin stribe plus en dublet-0 at rulle ind i. Det er
   * dubletten der gør at 9 → 0 kan rulle FORLÆNS i stedet for at springe
   * baglæns gennem 8-7-6.
   *
   * «01:12» = fire hjul med cyklus 10, 10, 6, 10. Hvert 10-hjul bærer '0'
   * to gange (0 og dubletten), det 6-cyklus hjul ligeså.
   *
   * MUT: fjern dubletten (`i < cyklus` i stedet for `i <= cyklus`) → '0'
   * findes fire gange i stedet for otte → fanger.
   */
  it('hvert hjul bærer hele striben PLUS en dublet-0', async () => {
    const s = await render(<RullendeUr sek={72} farve="#fff" tegnFarve="#888" />)
    expect(s.getAllByText('0')).toHaveLength(8)
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

})
