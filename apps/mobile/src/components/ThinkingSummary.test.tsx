import { act, fireEvent, render } from '@testing-library/react-native'
import { ThinkingSummary } from './ThinkingSummary'

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
    expect(screen.getByText(/^Tænker\.+\s*$/)).toBeTruthy()
  })

  it('prikkerne holder FAST bredde — etiketten maa ikke hoppe', async () => {
    const screen = await render(<ThinkingSummary text="noget" live />)
    const t = screen.getByText(/^Tænker/)
    expect(String(t.props.children)).toHaveLength('Tænker'.length + 3)
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

it('et tiendedels sekund ER en maaling og vises', async () => {
  const s = await render(<ThinkingSummary seconds={0.1} text="kort" />)
  expect(s.getByText(/Tænkte i 0,1 s/)).toBeTruthy()
})
