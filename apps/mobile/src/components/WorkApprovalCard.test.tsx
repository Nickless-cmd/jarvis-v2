import { fireEvent, render } from '@testing-library/react-native'
import { WorkApprovalCard } from './WorkApprovalCard'
import type { CapabilityApproval, ToolIntentApproval } from '../lib/mcTypes'

const NOW = new Date('2026-09-02T12:05:00Z')

const cap = (over: Partial<CapabilityApproval> = {}): CapabilityApproval => ({
  request_id: 'cap-1',
  approval_system: 'capability',
  status: 'pending',
  active: true,
  stale: false,
  requested_at: '2026-09-02T12:00:00Z',
  initiated_by: 'jarvis-self',
  scheduled_for_user_id: 'bjorn',
  capability_id: 'tool:run-non-destructive-command',
  capability_name: 'run non-destructive command',
  capability_kind: 'tool',
  execution_mode: 'sudo-exec-proposal',
  approval_policy: 'required',
  run_id: 'visible-1',
  proposal_target_path: 'sudo',
  proposal_content: 'sudo head -n 5 /root/.profile',
  proposal_content_summary: 'sudo head -n 5 /root/.profile',
  proposal_reason: 'Vil du godkende, at jeg læser de første fem linjer?',
  approved_at: null,
  executed: 0,
  executed_at: null,
  ...over
})

const intent = (over: Partial<ToolIntentApproval> = {}): ToolIntentApproval => ({
  request_id: 'ti-1',
  approval_system: 'tool-intent',
  status: 'pending',
  active: true,
  stale: false,
  requested_at: '2026-09-02T12:00:00Z',
  initiated_by: 'jarvis-self',
  scheduled_for_user_id: null,
  approval_id: 'tool-intent-approval-1',
  intent_key: 'tool-intent::abc',
  intent_type: 'inspect-working-tree',
  intent_target: '(detached)',
  approval_scope: 'repo-read',
  approval_state: 'pending',
  approval_reason: 'Intent remains proposal-only.',
  expires_at: '2026-09-02T12:15:00Z',
  execution_state: 'not-executed',
  ...over
})

const noop = () => {}

it('viser anledning, tag og kommando (R8-mønsteret)', async () => {
  const s = await render(
    <WorkApprovalCard approval={cap()} onApprove={noop} onSkip={noop} now={NOW} />
  )
  expect(s.getByText(/godkende, at jeg læser/)).toBeTruthy()
  expect(s.getByText('sudo-exec-proposal')).toBeTruthy()
  expect(s.getByText('sudo head -n 5 /root/.profile')).toBeTruthy()
})

it('rendrer også et tool-intent-kort med sit eget vindue', async () => {
  const s = await render(
    <WorkApprovalCard approval={intent()} onApprove={noop} onSkip={noop} now={NOW} />
  )
  expect(s.getByText('repo-read')).toBeTruthy()
  expect(s.queryByTestId('expiry-note')).not.toBeNull()
})

it('et udløbet kort tilbyder INGEN knap — det er hele pointen', async () => {
  const s = await render(
    <WorkApprovalCard
      approval={intent({ status: 'expired', stale: true, active: false })}
      onApprove={noop}
      onSkip={noop}
      now={NOW}
    />
  )
  expect(s.queryByLabelText('Godkend')).toBeNull()
  expect(s.getByTestId('dead-note')).toBeTruthy()
})

it('godkend og spring over melder tilbage med kortet', async () => {
  const onApprove = jest.fn()
  const onSkip = jest.fn()
  const a = cap()
  const s = await render(
    <WorkApprovalCard approval={a} onApprove={onApprove} onSkip={onSkip} now={NOW} />
  )
  await fireEvent.press(s.getByLabelText('Godkend'))
  await fireEvent.press(s.getByLabelText('Spring over'))
  expect(onApprove).toHaveBeenCalledWith(a)
  expect(onSkip).toHaveBeenCalledWith(a)
})

it('knappen låses mens den arbejder', async () => {
  const onApprove = jest.fn()
  const s = await render(
    <WorkApprovalCard approval={cap()} busy onApprove={onApprove} onSkip={noop} now={NOW} />
  )
  expect(s.getByText('Godkender…')).toBeTruthy()
  await fireEvent.press(s.getByLabelText('Godkend'))
  expect(onApprove).not.toHaveBeenCalled()
})
