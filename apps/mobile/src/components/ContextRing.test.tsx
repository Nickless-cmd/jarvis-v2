import { render } from '@testing-library/react-native'
import { ContextRing, kontekstAndel } from './ContextRing'

const brug = (tokens: number, compactAt: number, compacting = false) =>
  ({ tokens, compactAt, compacting })

it('andelen maales mod compactAt, ikke mod modellens fulde vindue', () => {
  // 65.000 af 130.000 er HALVVEJS til komprimering. Maalte man mod et fuldt
  // 200k-vindue ville den samme samtale staa paa 32 % i det oejeblik den blev
  // komprimeret - og saa loej ringen om praecis det den findes for.
  expect(kontekstAndel(brug(65_000, 130_000))).toBe(0.5)
})

it('INTET svar giver null, ikke nul', () => {
  // Tom ring og INGEN ring betyder to forskellige ting.
  expect(kontekstAndel(null)).toBeNull()
  expect(kontekstAndel(undefined)).toBeNull()
})

it('en naevner paa nul er «uvist», ikke «0 %»', () => {
  expect(kontekstAndel(brug(4_000, 0))).toBeNull()
})

it('klemmer over 100 % ned til 1', () => {
  // Transcript kan naa forbi graensen foer fejeren har kigget.
  expect(kontekstAndel(brug(140_000, 130_000))).toBe(1)
})

it('tegner ingenting naar der ikke er noget at vise', async () => {
  const screen = await render(<ContextRing brug={null} />)
  expect(screen.queryByTestId('context-ring')).toBeNull()
})

it('tegner ringen naar der ER noget', async () => {
  const screen = await render(<ContextRing brug={brug(65_000, 130_000)} />)
  expect(screen.getByTestId('context-ring')).toBeTruthy()
  expect(screen.getByLabelText('Kontekst 50 procent fuld')).toBeTruthy()
})

// ÉN render pr. test. To render() i samme test efterlader to traeer, og RNTL's
// oprydning rammer dem ikke begge - alt efter den test bliver blindt.
it('buen daekker praecis halvdelen af omkredsen ved 50 %', async () => {
  const screen = await render(<ContextRing brug={brug(65_000, 130_000)} />)
  const bue = screen.getByTestId('context-ring-bue').props
  const omkreds = Number(bue.strokeDasharray)
  // offset = omkreds * (1 - andel). Fuld offset = tom ring.
  expect(Number(bue.strokeDashoffset)).toBeCloseTo(omkreds / 2, 5)
})
