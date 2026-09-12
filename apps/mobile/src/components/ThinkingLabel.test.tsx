import { render } from '@testing-library/react-native'
import { ThinkingLabel } from './ThinkingLabel'
import * as rm from '../lib/useReducedMotion'

it('viser ordet — ikke en spinner', async () => {
  const s = await render(<ThinkingLabel />)
  expect(s.getByTestId('thinking-label')).toBeTruthy()
  expect(s.getByText('Tænker')).toBeTruthy()
})

it('kan få sit eget ord', async () => {
  const s = await render(<ThinkingLabel label="Undersøger" />)
  expect(s.getByText('Undersøger')).toBeTruthy()
})

it('reduceret bevægelse slukker sweepet men beholder ordet', async () => {
  jest.spyOn(rm, 'useReducedMotion').mockReturnValue(true)
  const s = await render(<ThinkingLabel />)
  expect(s.getByText('Tænker')).toBeTruthy()
  expect(s.queryByTestId('thinking-label')).toBeNull()
  jest.restoreAllMocks()
})

/**
 * Bjørn 13/9-2026: «fjern lys bølge helt fra tænker linje over composer men
 * behold i chatview tool results og tænker/tænkte linje med lys bølge».
 *
 * Linjen over skrivefeltet skifter i forvejen indhold hele tiden — værktøjets
 * etiket, «Arbejder», tankestrømmen — og bærer sin egen prik-sekvens. Et lys
 * ovenpå dét er ét signal for meget netop dér hvor øjet hviler mest.
 */
it('linjen over skrivefeltet har INTET lys', async () => {
  const s = await render(<ThinkingLabel label="Kører kommando: sleep" />)
  expect(s.queryByTestId('glidende-lys')).toBeNull()
  expect(s.queryByTestId('glidende-tekst')).toBeNull()
  expect(s.getByText('Kører kommando: sleep')).toBeTruthy()
})
