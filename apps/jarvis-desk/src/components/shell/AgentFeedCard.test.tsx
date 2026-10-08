import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, waitFor } from '@testing-library/react'
import { AgentFeedCardBody } from './AgentFeedCard'
import { getTotpStatus } from '../../lib/totpApi'
import type { FeedCard } from '../../lib/agentContractApi'
import type { ApiConfig } from '../../lib/api'

vi.mock('../../lib/totpApi', () => ({ getTotpStatus: vi.fn() }))
vi.mock('../../lib/agentContractApi', () => ({
  afgoerAgentApproval: vi.fn(),
  bucketLabel: (b: string) => b,
}))

const cfg = { apiBaseUrl: 'http://x', authToken: 't' } as ApiConfig

/** Et ventende agent-approval-kort — formen `agent_contract_projection.feed` bygger. */
function kort(): FeedCard {
  return {
    ref_kind: 'approval', ref_id: 'appr-1', section: 'venter', bucket: 'approval',
    agent_id: 'a1', assignment_id: 'asg-1', origin_session_id: 's1',
    title: 'Godkend: bash', reason: 'Venter på din godkendelse',
    summary: 'bash({"command": "sed -n 1,5p x"})', error: null,
    updated_at: '2026-10-08T13:42:33Z', created_at: '2026-10-08T13:42:33Z',
    approval: { approval_id: 'appr-1', digest: 'd', risk_class: 'write',
                expires_at: '2026-10-10T13:42:33Z', tool_name: 'bash', status: 'pending' },
    state: { read: false, acknowledged: false, model_claim: '', assignment_status: '' },
    can_acknowledge: false,
  } as FeedCard
}

function tegn() {
  return render(<AgentFeedCardBody config={cfg} card={kort()} onChanged={() => {}} onError={() => {}} />)
}

const kodeFelt = (c: HTMLElement) => c.querySelector('input[aria-label="Totrinskode"]')

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('AgentFeedCard — totrinskode-feltet', () => {
  it('skjuler kode-feltet naar brugeren IKKE har sat totrin op', async () => {
    // Maalt 8/10-2026: feltet blev tegnet UBETINGET, saa Bjoern blev bedt om en
    // sekscifret kode han ikke havde — i et kort hvor ruten springer den over.
    vi.mocked(getTotpStatus).mockResolvedValue({ configured: false, account: null })
    const { container } = tegn()
    await waitFor(() => expect(kodeFelt(container)).toBeNull())
    expect(container.textContent).toContain('Godkend')      // handlingerne er der stadig
    expect(container.textContent).toContain('Afvis')
  })

  it('viser kode-feltet naar brugeren HAR sat totrin op', async () => {
    vi.mocked(getTotpStatus).mockResolvedValue({ configured: true, account: 'Bjørn' })
    const { container } = tegn()
    await waitFor(() => expect(kodeFelt(container)).not.toBeNull())
  })

  it('viser feltet naar status ikke kan afgoeres — en godkendelse maa ikke blokeres', async () => {
    vi.mocked(getTotpStatus).mockRejectedValue(new Error('nede'))
    const { container } = tegn()
    await waitFor(() => expect(kodeFelt(container)).not.toBeNull())
  })
})
