import { act, fireEvent, render } from '@testing-library/react-native'
import { KORT_TAERSKEL_S, ThinkingSummary } from './ThinkingSummary'

describe('ThinkingSummary', () => {
  it('viser varigheden', async () => {
    const screen = await render(<ThinkingSummary seconds={14} text="hm" />)
    expect(screen.getByText('Tænkte i 14 s')).toBeTruthy()
  })

  it('bruger dansk komma og skjuler tom decimal', async () => {
    const a = await render(<ThinkingSummary seconds={3.4} text="x" />)
    expect(a.getByText('Tænkte i 3,4 s')).toBeTruthy()
  })

  it('skifter til minutter over 60 s', async () => {
    const screen = await render(<ThinkingSummary seconds={95} text="x" />)
    expect(screen.getByText('Tænkte i 1 min 35 s')).toBeTruthy()
  })

  // Uden en måling skriver vi ikke «Tænkte» — det ville være en paastand vi
  // ikke har daekning for.
  // 12/9-2026: en blok med tekst men uden maalt varighed skal VISES —
  // før returnerede den null, og tænkningen forsvandt tavst.
  // Kun helt tom input (ingen tekst, ingen seconds, ikke live) skjules.
  it('viser «Tænkte» uden maalt varighed men med tekst', async () => {
    const a = await render(<ThinkingSummary text="noget" />)
    expect(a.getByTestId('thinking-summary')).toBeTruthy()
    expect(a.getByText('Tænkte')).toBeTruthy()
    const b = await render(<ThinkingSummary seconds={0} text="noget" />)
    expect(b.getByTestId('thinking-summary')).toBeTruthy()
  })

  it('viser INTET når der slet intet er', async () => {
    const a = await render(<ThinkingSummary />)
    expect(a.queryByTestId('thinking-summary')).toBeNull()
  })

  it('traadens linje er ROLIG — «Tænker» og prikker, ikke raa monolog', async () => {
    // Selve tankestroemmen staar over komponisten. Traaden skal kunne laeses
    // mens han taenker, og monolog der flimrer i den goer den ulaeselig.
    const screen = await render(<ThinkingSummary text={'foerst\njeg tænker nu'} live />)
    expect(screen.queryByText('jeg tænker nu')).toBeNull()
    expect(screen.getByText('Tænker')).toBeTruthy()
  })

  // Bjørn 19/9-2026: tanke-linjen skal ligne runde-linjen. Prikkerne står
  // derfor i cellen ude til højre (de rullende), ikke som tegn i teksten —
  // så kan etiketten heller ikke hoppe.
  it('prikkerne står i cellen, som på runde-linjen', async () => {
    const screen = await render(<ThinkingSummary text="noget" live />)
    expect(screen.getByText('Tænker')).toBeTruthy()
    expect(screen.getByTestId('prikker', { includeHiddenElements: true })).toBeTruthy()
  })

  it('færdig: én caret i cellen, ikonet i sin faste celle', async () => {
    const screen = await render(<ThinkingSummary seconds={9} text="x" />)
    expect(screen.queryByTestId('prikker', { includeHiddenElements: true })).toBeNull()
    expect(screen.getByTestId('thinking-caret')).toBeTruthy()
  })

  it('går fra tom til live uden at vælte (hooks før return)', async () => {
    const screen = await render(<ThinkingSummary />)
    await screen.rerender(<ThinkingSummary live text="a" />)
    expect(screen.getByText('Tænker')).toBeTruthy()
  })

  it('folder teksten ud og sammen igen', async () => {
    const screen = await render(<ThinkingSummary seconds={9} text="min overvejelse" />)
    expect(screen.queryByText('min overvejelse')).toBeNull()

    await act(async () => { fireEvent.press(screen.getByTestId('thinking-summary')) })
    expect(screen.getByText('min overvejelse')).toBeTruthy()

    await act(async () => { fireEvent.press(screen.getByTestId('thinking-summary')) })
    expect(screen.queryByText('min overvejelse')).toBeNull()
  })

  it('uden tekst er linjen ikke tryk-bar', async () => {
    const screen = await render(<ThinkingSummary seconds={5} />)
    expect(screen.getByTestId('thinking-summary').props.accessibilityState?.disabled).toBe(true)
  })
})

/**
 * Målt på Bjørns skærm 13/9-2026: to rækker sagde «Tænkte i 0 s» fordi tanken
 * var lynhurtig. Nul sekunder er ikke en måling man kan stå inde for — samme
 * skel som `undefined` vs `0` alle andre steder i den her kæde.
 */
it('en tanke under et tiendedels sekund faar ingen tid', async () => {
  const s = await render(<ThinkingSummary seconds={0.04} text="lyn" />)
  expect(s.getByText('Tænkte')).toBeTruthy()
  expect(s.queryByText(/0 s/)).toBeNull()
})

it('et tiendedels sekund ER en maaling — men under taersklen vises tallet ikke', async () => {
  // Den oprindelige test skelnede «0 s» (en paastand uden daekning) fra
  // «0,1 s» (en aegte maaling) og kraevede at den sidste blev VIST. Den
  // skelnen staar stadig i koden — `hasSeconds` er uaendret — men fra 14/9
  // afgoer en anden regel om tallet naar skaermen: under tre sekunder er
  // talraekken stoej, og etiketten siger bare «Tænkte».
  //
  // Raekken er der uanset. Det er tallet der forsvinder, ikke doeren.
  const s = await render(<ThinkingSummary seconds={0.1} text="kort" />)
  expect(s.getByText('Tænkte')).toBeTruthy()
  expect(s.queryByText(/0,1 s/)).toBeNull()
})

// ─────────────────────────────────────────────────────────────────────────
// Korte tanker staar STILLE (14/9-2026)
//
// Jarvis maalte Bjoerns skaerm: tre «Tænkte i X s» paa ét billede (1,5 / 2,6 /
// 1,1 s), tre af 31 baand der siger naesten det samme. De stjaeler
// opmaerksomhed fra de linjer der baerer indhold.
//
// Men baandet er ogsaa DOEREN til selve tanken. Maalt paa 1.511 taenke-blokke:
// 67 % er under tre sekunder — og de korte er IKKE tomme, median 457 tegn,
// nul tomme. At skjule dem ville ikke fjerne stoej, det ville skjule 1.018
// tanker.
//
// Derfor: de korte mister deres TAL, ikke deres plads. «Tænkte» i stedet for
// «Tænkte i 1,1 s» — den gentagne talraekke var stoejen, doeren er ikke.
// ─────────────────────────────────────────────────────────────────────────

describe('korte tanker', () => {
  it('under taersklen vises INTET tal', async () => {
    const s = await render(<ThinkingSummary seconds={1.1} text="en rigtig tanke" />)
    expect(s.getByText('Tænkte')).toBeTruthy()
    expect(s.queryByText('Tænkte i 1,1 s')).toBeNull()
  })

  it('men doeren er der stadig — teksten kan foldes ud', async () => {
    const s = await render(<ThinkingSummary seconds={1.1} text="en rigtig tanke" />)
    await act(async () => { fireEvent.press(s.getByText('Tænkte')) })
    expect(s.getByText('en rigtig tanke')).toBeTruthy()
  })

  it('PAA taersklen vises tallet', async () => {
    const s = await render(<ThinkingSummary seconds={3} text="x" />)
    expect(s.getByText('Tænkte i 3 s')).toBeTruthy()
  })

  it('over taersklen vises tallet', async () => {
    const s = await render(<ThinkingSummary seconds={8.3} text="x" />)
    expect(s.getByText('Tænkte i 8,3 s')).toBeTruthy()
  })

  it('en LIVE tanke er uroert — den siger «her arbejdes»', async () => {
    const s = await render(<ThinkingSummary seconds={0.5} text="x" live />)
    expect(s.queryByText('Tænkte')).toBeNull()
  })

  it('taersklen er maalt, ikke valgt paa foelelsen', () => {
    // 67 % af 1.511 maalte blokke ligger under tre sekunder; 90.-percentilen
    // er 8,3 s. Taersklen skiller stoejen fra de aegte pauser.
    expect(KORT_TAERSKEL_S).toBe(3)
  })
})
