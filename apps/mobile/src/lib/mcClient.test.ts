import { ApiError } from './apiClient'
import { approveRequest, approveToolIntent, fetchApprovals, fetchRuns, pendingApprovals } from './mcClient'
import { approvalDetail, approvalReason, approvalTag, isActionable, isCapability } from './mcTypes'
import type { Approval, CapabilityApproval, ToolIntentApproval } from './mcTypes'
import type { ApiConfig } from './types'

const config: ApiConfig = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }

const ok = (body: unknown) => ({ ok: true, status: 200, json: async () => body })

beforeEach(() => {
  global.fetch = jest.fn()
})

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
  proposal_reason: 'Sudo-near command was captured as a proposal only.',
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

describe('fetchRuns', () => {
  it('sender limit og pakker svaret ud', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue(
      ok({ active_run: null, last_outcome: null, recent_runs: [{ run_id: 'r1' }], summary: { active: false, recent_count: 1, failed_count: 0 } })
    )
    const res = await fetchRuns(config, 20)
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('/mc/runs?limit=20')
    expect(res.recent_runs).toHaveLength(1)
  })

  it('overlever et svar uden felter', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue(ok({}))
    const res = await fetchRuns(config)
    expect(res.recent_runs).toEqual([])
    expect(res.summary.recent_count).toBe(0)
  })
})

describe('fetchApprovals', () => {
  it('henter begge godkendelsessystemer i én liste', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue(
      ok({ requests: [cap(), intent()], summary: { pending_count: 2, approved_count: 0, request_count: 2 } })
    )
    const res = await fetchApprovals(config)
    expect(res.requests.map((r) => r.approval_system)).toEqual(['capability', 'tool-intent'])
  })
})

describe('approveRequest', () => {
  it('bruger approve-and-execute — ikke approve alene', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue(ok({ ok: true }))
    await approveRequest(config, 'cap-1')
    const url = (global.fetch as jest.Mock).mock.calls[0][0] as string
    expect(url).toContain('/approve-and-execute')
    expect((global.fetch as jest.Mock).mock.calls[0][1].method).toBe('POST')
  })

  it('id\'et url-enkodes', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue(ok({ ok: true }))
    await approveRequest(config, 'cap/1 2')
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain('cap%2F1%202')
  })

  it('404 bliver til en besked et menneske kan forstå', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 404, json: async () => ({}) })
    await expect(approveRequest(config, 'væk')).rejects.toThrow('findes ikke længere')
  })
})

describe('approveToolIntent', () => {
  it('409 forklares som et udløbet vindue', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValue({ ok: false, status: 409, json: async () => ({}) })
    await expect(approveToolIntent(config)).rejects.toThrow('udløbet')
  })
})

describe('pendingApprovals', () => {
  it('skjuler døde kort — det er hele pointen med køen', () => {
    const list: Approval[] = [
      cap(),
      cap({ request_id: 'cap-2', active: false, status: 'approved' }),
      intent({ request_id: 'ti-2', stale: true, status: 'expired' })
    ]
    expect(pendingApprovals(list).map((a) => a.request_id)).toEqual(['cap-1'])
  })
})

describe('felt-udtræk på tværs af de to systemer', () => {
  it('capability: navn, anledning, kommando, tag', () => {
    const a = cap()
    expect(isCapability(a)).toBe(true)
    expect(approvalReason(a)).toContain('proposal only')
    expect(approvalDetail(a)).toBe('sudo head -n 5 /root/.profile')
    expect(approvalTag(a)).toBe('sudo-exec-proposal')
  })

  it('tool-intent: samme funktioner, andre felter', () => {
    const a = intent()
    expect(approvalReason(a)).toContain('proposal-only')
    expect(approvalDetail(a)).toBe('(detached)')
    expect(approvalTag(a)).toBe('repo-read')
  })

  it('falder tilbage på proposal_content når summary er tom', () => {
    expect(approvalDetail(cap({ proposal_content_summary: '' }))).toBe('sudo head -n 5 /root/.profile')
  })

  it('et udløbet kort er aldrig handlingsbart', () => {
    expect(isActionable(intent({ stale: true }))).toBe(false)
    expect(isActionable(cap({ active: false }))).toBe(false)
    expect(isActionable(cap())).toBe(true)
  })
})
