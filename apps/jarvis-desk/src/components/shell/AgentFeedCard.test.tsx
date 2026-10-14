import { afterEach, describe, expect, it, vi } from 'vitest'
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react'
import { AgentFeedCardBody } from './AgentFeedCard'
import { afgoerAgentApproval, type FeedCard } from '../../lib/agentContractApi'
import type { ApiConfig } from '../../lib/api'

/**
 * Kode-feltet er VÆK (14/10-2026).
 *
 * Denne fil pinnede indtil i dag at et totrinskode-felt blev skjult eller vist alt
 * efter om brugeren havde sat totrin op. Det var en fejl hele vejen igennem: ruten
 * krævede koden ved HVER godkendelse, og Bjørn skulle derfor finde telefonen for at
 * svare på noget han sad foran. Hans egen spec (§6.1) siger det modsatte — TOTP
 * hører til en FREMMED session; ejeren i sin egen desk-session har fri adgang, fordi
 * sessionen allerede er bundet til ham.
 *
 * Det der bærer sikkerheden nu er identiteten OG sessionen: afgørelsen sendes med
 * den samtale posten hører til (`origin_session_id`), og serveren afviser et svar fra
 * en anden. Derfor måler testen her at SESSIONEN følger med — ikke en kode.
 */
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

afterEach(() => { cleanup(); vi.restoreAllMocks() })

describe('AgentFeedCard — godkendelsen', () => {
  it('har Godkend og Afvis — og INTET kode-felt', () => {
    const { container } = tegn()
    expect(container.querySelector('input[aria-label="Totrinskode"]')).toBeNull()
    expect(screen.getByRole('button', { name: 'Godkend' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Afvis' })).toBeInTheDocument()
  })

  it('sender kortets egen session med afgørelsen — ikke en kode', async () => {
    vi.mocked(afgoerAgentApproval).mockResolvedValue({ status: 'ok', approval: { status: 'approved' } })
    tegn()
    fireEvent.click(screen.getByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(afgoerAgentApproval)
      .toHaveBeenCalledWith(cfg, 'appr-1', 'approve', 'd', 's1'))
  })

  it('Afvis bærer samme session — afvisningen er bundet til posten, ikke til et svar', async () => {
    vi.mocked(afgoerAgentApproval).mockResolvedValue({ status: 'ok', approval: { status: 'denied' } })
    tegn()
    fireEvent.click(screen.getByRole('button', { name: 'Afvis' }))
    await waitFor(() => expect(afgoerAgentApproval)
      .toHaveBeenCalledWith(cfg, 'appr-1', 'deny', 'd', 's1'))
  })
})
