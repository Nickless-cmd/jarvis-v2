import { render } from '@testing-library/react-native'
import { RunResumeCard } from './RunResumeCard'
import type { RunResume } from '../lib/runResume'

const r = (o: Partial<RunResume> = {}): RunResume => ({
  udfald: 'lykkedes', sekunder: 187, runder: 9, vaerktoejskald: 18,
  vaerktoejer: [{ navn: 'bash', antal: 12 }, { navn: 'read_file', antal: 6 }],
  godkendelser: 0, fejl: [], ...o,
})

it('siger udfald og varighed', async () => {
  const screen = await render(<RunResumeCard resume={r()} />)
  expect(screen.getByText('Lykkedes')).toBeTruthy()
  expect(screen.getByText('3 min 07 s')).toBeTruthy()
})

it('UDEN fejl er der ingen fejlboks', async () => {
  // Et felt der er tomt i ni ud af ti tilfaelde maa ikke staa der.
  const screen = await render(<RunResumeCard resume={r()} />)
  expect(screen.queryByText(/kvote/)).toBeNull()
})

it('MED fejl vises de', async () => {
  const screen = await render(<RunResumeCard resume={r({ udfald: 'fejlede', fejl: ['kvote opbrugt'] })} />)
  expect(screen.getByText('kvote opbrugt')).toBeTruthy()
  expect(screen.getByText('Fejlede')).toBeTruthy()
})

it('AFBRUDT er gul, ikke roed', async () => {
  // Roedt paa noget man selv standsede goer farven ubrugelig.
  const { StyleSheet } = require('react-native')
  const screen = await render(<RunResumeCard resume={r({ udfald: 'afbrudt' })} />)
  expect(StyleSheet.flatten(screen.getByText('Afbrudt').props.style).color).toBe('#FFB347')
})

it('FEJLET er roed', async () => {
  const { StyleSheet } = require('react-native')
  const screen = await render(<RunResumeCard resume={r({ udfald: 'fejlede' })} />)
  expect(StyleSheet.flatten(screen.getByText('Fejlede').props.style).color).toBe('#ff8080')
})

it('godkendelser vises kun naar der VAR nogen', async () => {
  const screen = await render(<RunResumeCard resume={r({ godkendelser: 0 })} />)
  expect(screen.queryByText('godkendelser')).toBeNull()
})

it('vaerktoejerne staar med flest foerst', async () => {
  const screen = await render(<RunResumeCard resume={r()} />)
  expect(screen.getByText('bash ×12  ·  read_file ×6')).toBeTruthy()
})

it('ukendt varighed skriver ingenting frem for «0 s»', async () => {
  const screen = await render(<RunResumeCard resume={r({ sekunder: null })} />)
  expect(screen.queryByText('0 s')).toBeNull()
})
