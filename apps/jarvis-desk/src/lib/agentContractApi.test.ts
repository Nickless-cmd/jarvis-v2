import { afterEach, describe, expect, it, vi } from 'vitest'
import fixture from './__fixtures__/agentContract.json'
import {
  afgoerAgentApproval, bucketLabel, erKontraktAaben, erKontraktAktiv, getKontraktAgent, kontraktBesked,
  kontraktVarighed, kvitteringTekst,
  type ContractAgentRow, type ContractApproval, type ContractCounts, type ContractDetail, type ContractReceipt,
  type FeedCard,
} from './agentContractApi'
import { StreamError } from './streamClient'

const cfg = { apiBaseUrl: 'http://test', authToken: 't' }

afterEach(() => vi.unstubAllGlobals())

// ── Feltnavne pinnet mod den RIGTIGE rute-respons (fixturen genereres af backend-testen) ────────────────────
// `Record<keyof T, true>` tvinger en post pr. felt: tilføjes eller fjernes et felt i typen, fejler tsc her, og
// sammenligningen mod fixturen fejler hvis serveren sender noget andet end typen siger.
const ROW: Record<keyof ContractAgentRow, true> = {
  agent_id: true, parent_agent_id: true, role: true, goal: true, council_id: true, children: true,
  lifecycle_status: true, target: true, assignment_id: true, assignment_status: true, origin_session_id: true,
  run_id: true, run_status: true, attempts: true, bucket: true, attention: true, reason: true, error: true,
  started_at: true, finished_at: true, duration_s: true, updated_at: true, heartbeat: true, tokens: true,
  cost_usd: true, route: true, last_message: true, summary: true, pending_approvals: true, model_claim: true,
  read: true, acknowledged: true,
}
const COUNTS: Record<keyof ContractCounts, true> = {
  active: true, queued: true, waiting: true, blocked: true, attention: true, open: true,
}
const CARD: Record<keyof FeedCard, true> = {
  ref_kind: true, ref_id: true, section: true, bucket: true, agent_id: true, assignment_id: true,
  origin_session_id: true, title: true, reason: true, summary: true, error: true, updated_at: true,
  created_at: true, approval: true, state: true, can_acknowledge: true,
}
const RECEIPT: Record<keyof ContractReceipt, true> = {
  kind: true, accepted: true, confirmed: true, code: true, state: true, delivered: true,
}
const DETAIL: Record<keyof ContractDetail, true> = {
  status: true, agent: true, assignments: true, runs: true, messages: true, tool_calls: true, approvals: true,
  artifacts: true, children: true, capability: true, contract_version: true,
}
const APPROVAL: Record<keyof ContractApproval, true> = {
  approval_id: true, kind: true, status: true, agent_id: true, assignment_id: true, run_id: true,
  parent_run_id: true, origin_session_id: true, target: true, tool_name: true, safe_view: true,
  args_digest: true, risk_class: true, requested_by: true, created_at: true, expires_at: true,
  decided_at: true, decided_by: true, decision_note: true,
}
const sorted = (o: object) => Object.keys(o).sort()

describe('agentContractApi — typerne dækker præcis det serveren sender', () => {
  it('overview-rækken, tællerne, detaljen, approvalen, kortet og kvitteringen', () => {
    expect(sorted(fixture.overview.agents[0]!)).toEqual(sorted(ROW))
    expect(sorted(fixture.overview.counts)).toEqual(sorted(COUNTS))
    expect(sorted(fixture.detail)).toEqual(sorted(DETAIL))
    expect(sorted(fixture.detail.approvals[0]!)).toEqual(sorted(APPROVAL))
    // `approval` findes kun på approval-kort; agentkort har det ikke.
    expect(sorted(fixture.feed.cards[0]!)).toEqual(sorted(CARD).filter((k) => k !== 'approval'))
    expect(sorted(fixture.feed.approval_card)).toEqual(sorted(CARD))
    expect(sorted(fixture.message.receipt)).toEqual(sorted(RECEIPT))
    expect(sorted(fixture.stop.receipt)).toEqual(sorted(RECEIPT))
  })

  it('serverens tilstande har alle en tekst, og en ukendt vises som den er — aldrig som succes', () => {
    for (const b of ['idle', 'queued', 'active', 'settling', 'retry_pending', 'waiting_for_client',
      'waiting_for_approval', 'waiting_for_budget', 'outcome_unknown', 'done', 'failed', 'timed_out',
      'cancelled', 'unknown']) expect(bucketLabel(b)).not.toBe(b)
    expect(bucketLabel('noget-nyt')).toBe('noget-nyt')
  })
})

describe('klassifikation i klienten (kun visning — serveren afgør bucket)', () => {
  it('aktive og åbne er ikke det samme som opmærksomhed', () => {
    expect(['active', 'settling', 'retry_pending'].every(erKontraktAktiv)).toBe(true)
    expect(['queued', 'waiting_for_approval', 'outcome_unknown', 'failed'].some(erKontraktAktiv)).toBe(false)
    expect(erKontraktAaben({ assignment_status: 'waiting' })).toBe(true)
    expect(erKontraktAaben({ assignment_status: 'failed' })).toBe(false)
    expect(erKontraktAaben({ assignment_status: 'completed' })).toBe(false)
  })
  it('varighed', () => {
    expect([null, 5, 75, 3720].map(kontraktVarighed)).toEqual(['', '5s', '1m 15s', '1t 2m'])
  })
})

describe('kvittering', () => {
  const base: ContractReceipt = { kind: 'stop', accepted: true, confirmed: false, code: '', state: '', delivered: null }
  it('accept er hverken levering eller stop — det står i teksten', () => {
    expect(kvitteringTekst({ ...base, kind: 'message', delivered: false })).toContain('Levering er ikke bekræftet')
    expect(kvitteringTekst(base)).toContain('ikke bekræftet stoppet')
    expect(kvitteringTekst({ ...base, accepted: false })).toBe('Serveren afviste anmodningen.')
  })
})

describe('fejloversættelse', () => {
  it('404 på en agent er «ingen kontrakt» (null), ikke en fejl — en gammel scout har ingen', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"Agenten findes ikke"}', { status: 404 })))
    expect(await getKontraktAgent(cfg, 'a1')).toBeNull()
  })

  it('en 500 er IKKE null: serverfejl må ikke se ud som «ingen kontrakt»', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('boom', { status: 500 })))
    await expect(getKontraktAgent(cfg, 'a1')).rejects.toBeInstanceOf(StreamError)
  })

  it('403 på en handling forklares, ikke «HTTP 403»', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{"detail":"x"}', { status: 403 })))
    await expect(kontraktBesked(cfg, 'a1', 'hej')).rejects.toThrow(/slukket|ret til/)
  })

  it('approval-afgørelsen bærer digest og kode, og fejlene forklares', async () => {
    const f = vi.fn().mockResolvedValue(new Response('{}', { status: 410 }))
    vi.stubGlobal('fetch', f)
    await expect(afgoerAgentApproval(cfg, 'ap1', 'approve', 'dig', '123456')).rejects.toThrow('udløbet')
    const [url, init] = f.mock.calls[0]!
    expect(String(url)).toBe('http://test/agents/approvals/ap1/decision')
    expect(JSON.parse(init.body)).toEqual({ decision: 'approve', digest: 'dig', kode: '123456' })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response('{}', { status: 403 })))
    await expect(afgoerAgentApproval(cfg, 'ap1', 'approve', 'dig', '')).rejects.toThrow(/totrinskode/)
  })

  it('ingen anmodning bærer ejer eller session', async () => {
    const f = vi.fn().mockResolvedValue(new Response('{"receipt":{}}', { status: 200 }))
    vi.stubGlobal('fetch', f)
    await kontraktBesked(cfg, 'a1', 'hej')
    const body = JSON.parse(f.mock.calls[0]![1].body)
    expect(body).toEqual({ content: 'hej' })
  })
})
