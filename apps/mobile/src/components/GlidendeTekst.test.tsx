import { fireEvent, render } from '@testing-library/react-native'
import { GlidendeTekst } from './GlidendeTekst'

jest.mock('../lib/useReducedMotion', () => ({ useReducedMotion: () => mockReduced }))
let mockReduced = false
beforeEach(() => { mockReduced = false })

it('teksten staar som ÉT stykke — ikke delt op pr. bogstav', async () => {
  // Foerste udgave delte den, og saa ville en skaermlaeser laese linjen
  // bogstav for bogstav og tekst-opslag fejle.
  const s = await render(<GlidendeTekst text="Tænker…" aktiv />)
  expect(s.getByText('Tænker…')).toBeTruthy()
})

it('INAKTIV har intet lys', async () => {
  const s = await render(<GlidendeTekst text="Tænkte i 9 s" aktiv={false} />)
  expect(s.queryByTestId('glidende-lys', { includeHiddenElements: true })).toBeNull()
  expect(s.getByText('Tænkte i 9 s')).toBeTruthy()
})

it('reduceret bevaegelse slaar lyset FRA — men teksten bliver', async () => {
  // En animation man har bedt systemet om at lade vaere med, er ikke en
  // effekt; det er en overtraedelse.
  mockReduced = true
  const s = await render(<GlidendeTekst text="Tænker…" aktiv />)
  // MAAL BREDDEN FOERST. Uden den er baandet vaek alligevel (bredde 0), og
  // testen ville bestaa uanset om reduced-motion blev respekteret - den
  // mutation slap netop igennem.
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  expect(s.queryByTestId('glidende-lys', { includeHiddenElements: true })).toBeNull()
  expect(s.getByText('Tænker…')).toBeTruthy()
})

it('lyset venter paa at bredden er MAALT', async () => {
  // Uden maalingen ville baandet enten staa stille eller skyde forbi kanten
  // paa en linje af ukendt laengde.
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  expect(s.queryByTestId('glidende-lys', { includeHiddenElements: true })).toBeNull()
})

it('naar bredden er maalt, glider lyset', async () => {
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  // `onLayout` sidder paa den YDRE View, ikke paa teksten.
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  // `includeHiddenElements`: baandet er skjult for tilgaengelighed, og RNTL
  // udelader skjulte elementer som standard. At det SKAL med her, er i sig
  // selv beviset for at skjulningen virker.
  expect(s.getByTestId('glidende-lys', { includeHiddenElements: true })).toBeTruthy()
})

it('lyset kan ikke trykkes paa og laeses ikke op', async () => {
  const s = await render(<GlidendeTekst text="Kører bash…" aktiv />)
  await fireEvent(s.getByTestId('glidende-tekst'), 'layout',
    { nativeEvent: { layout: { width: 200, height: 20 } } })
  const lys = s.getByTestId('glidende-lys', { includeHiddenElements: true })
  expect(lys.props.pointerEvents).toBe('none')
  expect(lys.props.accessibilityElementsHidden).toBe(true)
})
