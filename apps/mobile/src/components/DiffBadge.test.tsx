import { render } from '@testing-library/react-native'
import { DiffBadge, diffVaerdAtVise } from './DiffBadge'
import type { GitStatus } from '../lib/apiClient'

const g = (o: Partial<GitStatus> = {}): GitStatus => ({
  branch: 'main', dirty: 73, added: 2925, removed: 1407,
  isGit: true, repo: 'jarvis-v2', host: 'CheifOne', link: 'ok', ...o,
})

it('et RENT trae har ingen badge', () => {
  // En badge der altid staar der, holder man op med at laese. Den skal betyde
  // «der ligger noget uafsluttet» - og saa maa den ikke ogsaa kunne betyde
  // «der ligger ingenting».
  expect(diffVaerdAtVise(g({ dirty: 0, added: 0, removed: 0 }))).toBe(false)
})

it('ingen git betyder ingen badge', () => {
  expect(diffVaerdAtVise(null)).toBe(false)
  expect(diffVaerdAtVise(g({ isGit: false }))).toBe(false)
})

it('beroerte filer UDEN linjetal vises stadig', () => {
  // En tom fil der blev oprettet, eller en binaer fil numstat ikke kan taelle.
  expect(diffVaerdAtVise(g({ added: 0, removed: 0 }))).toBe(true)
})

it('viser filer, plus og minus', async () => {
  const screen = await render(<DiffBadge git={g()} />)
  expect(screen.getByText('73 filer ændret')).toBeTruthy()
  expect(screen.getByText('+2925')).toBeTruthy()
  expect(screen.getByText('−1407')).toBeTruthy()
})

it('ÉN fil boejes i ental', async () => {
  const screen = await render(<DiffBadge git={g({ dirty: 1 })} />)
  expect(screen.getByText('1 fil ændret')).toBeTruthy()
})

it('nul tilfoejede linjer skriver ikke «+0»', async () => {
  const screen = await render(<DiffBadge git={g({ added: 0 })} />)
  expect(screen.queryByText('+0')).toBeNull()
  expect(screen.getByText('−1407')).toBeTruthy()
})

it('tegner ingenting paa et rent trae', async () => {
  const screen = await render(<DiffBadge git={g({ dirty: 0 })} />)
  expect(screen.queryByTestId('diff-badge')).toBeNull()
})

it('groen og roed er SEMANTIK, ikke appens accent', async () => {
  // En diff maa ikke skifte betydning fordi nogen vaelger en anden
  // accentfarve i indstillingerne.
  const { StyleSheet } = require('react-native')
  const screen = await render(<DiffBadge git={g()} />)
  const plus = StyleSheet.flatten(screen.getByText('+2925').props.style)
  const minus = StyleSheet.flatten(screen.getByText('−1407').props.style)
  expect(plus.color).not.toBe(minus.color)
  expect(plus.color).toBe('#4CAF50')
  expect(minus.color).toBe('#ff8080')
})
