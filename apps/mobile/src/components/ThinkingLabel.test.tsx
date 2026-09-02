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
