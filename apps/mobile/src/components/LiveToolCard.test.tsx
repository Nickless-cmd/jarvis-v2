import { render } from '@testing-library/react-native'
import { LiveToolCard } from './LiveToolCard'
import type { LiveStep } from '../lib/streamReducer'

const s = (o: Partial<LiveStep> = {}): LiveStep =>
  ({ navn: 'bash', etiket: 'bash: npm test', skridt: 1, setAt: 1_000_000, ...o })

it('viser etiketten og hvor laenge det har koert', async () => {
  const screen = await render(<LiveToolCard step={s()} now={1_012_000} />)
  expect(screen.getByText('bash: npm test')).toBeTruthy()
  expect(screen.getByText('12s')).toBeTruthy()
})

it('lige startet er 0s, ikke et negativt tal', async () => {
  // Klientens og serverens ur behoever ikke vaere enige paa millisekundet.
  const screen = await render(<LiveToolCard step={s()} now={999_000} />)
  expect(screen.getByText('0s')).toBeTruthy()
})

it('kortet kan findes paa vaerktoejets navn', async () => {
  const screen = await render(<LiveToolCard step={s()} now={1_000_000} />)
  expect(screen.getByTestId('live-tool-bash')).toBeTruthy()
})
