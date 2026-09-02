import { render } from '@testing-library/react-native'
import { WorkTaskCard, isActive, sourceOf, statusColor } from './WorkTaskCard'
import { tokens } from '../theme/tokens'
import type { McRun } from '../lib/mcTypes'

const NOW = new Date('2026-09-02T12:05:00Z')

const run = (over: Partial<McRun> = {}): McRun => ({
  run_id: 'visible-1',
  lane: 'primary',
  provider: 'deepseek',
  model: 'deepseek-v4-flash',
  status: 'completed',
  started_at: '2026-09-02T12:00:00Z',
  finished_at: '2026-09-02T12:01:00Z',
  text_preview: 'Tjekkede disken.',
  ...over
})

describe('kilden aflæses af run-id-præfikset', () => {
  it('fordi visible_runs ikke HAR en source-kolonne', () => {
    expect(sourceOf(run({ run_id: 'visible-abc' }))).toBe('snak')
    expect(sourceOf(run({ run_id: 'autonomous-abc' }))).toBe('autonom')
    expect(sourceOf(run({ run_id: 'agent-abc' }))).toBe('agent')
  })
})

describe('aktiv-vurdering', () => {
  it('en kørsel uden sluttidspunkt kører stadig', () => {
    expect(isActive(run({ finished_at: null }))).toBe(true)
    expect(isActive(run({ status: 'running' }))).toBe(true)
    expect(isActive(run())).toBe(false)
  })
})

describe('statusfarver', () => {
  it('fejl og afbrydelse skiller sig ud fra normal afslutning', () => {
    expect(statusColor('running')).toBe(tokens.color.accent)
    expect(statusColor('failed')).toBe(tokens.color.error)
    expect(statusColor('cancelled')).toBe(tokens.color.warn)
    expect(statusColor('completed')).toBe(tokens.color.fg3)
  })
})

it('viser kilde, model, alder og forsmag', async () => {
  const s = await render(<WorkTaskCard run={run({ run_id: 'autonomous-x' })} now={NOW} />)
  expect(s.getByText('Autonom')).toBeTruthy()
  expect(s.getByText('deepseek-v4-flash')).toBeTruthy()
  expect(s.getByText('Tjekkede disken.')).toBeTruthy()
  expect(s.getByTestId('status-dot')).toBeTruthy()
})

it('tåler en kørsel uden opsummering', async () => {
  const s = await render(<WorkTaskCard run={run({ text_preview: null })} now={NOW} />)
  expect(s.getByText('Ingen opsummering endnu.')).toBeTruthy()
})
