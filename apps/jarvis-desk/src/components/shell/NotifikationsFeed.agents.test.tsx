import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import fixture from '../../lib/__fixtures__/agentContract.json'
import type { FeedCard } from '../../lib/agentContractApi'

const hent = vi.fn()
const hentHistorik = vi.fn()
vi.mock('../../lib/notifikationerApi', () => ({
  hentNotifikationer: (...a: unknown[]) => hent(...a),
  hentTidligere: (...a: unknown[]) => hentHistorik(...a),
  afgoerNotifikation: vi.fn(),
  setNotifikation: vi.fn(),
}))
const sockets: { onmessage: ((e: { data: string }) => void) | null; close: () => void }[] = []
vi.mock('../../lib/api', () => ({
  openEventSocket: () => {
    const s = { onmessage: null, onerror: null, close: vi.fn() }
    sockets.push(s as never)
    return s
  },
}))
const feed = vi.fn()
const laest = vi.fn()
const kvitter = vi.fn()
const afgoer = vi.fn()
vi.mock('../../lib/agentContractApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/agentContractApi')>('../../lib/agentContractApi')
  return {
    ...rigtig,
    getKontraktFeed: (...a: unknown[]) => feed(...a),
    markerKontraktLaest: (...a: unknown[]) => laest(...a),
    kvitterKontrakt: (...a: unknown[]) => kvitter(...a),
    afgoerAgentApproval: (...a: unknown[]) => afgoer(...a),
  }
})

import { NotifikationsFeed } from './NotifikationsFeed'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
// Kortformen er den RIGTIGE rute-respons (agentContract.json genereres af backend-testen).
const agentSkabelon = fixture.feed.cards[1] as unknown as FeedCard
const approvalSkabelon = fixture.feed.approval_card as unknown as FeedCard
const kort = (o: Partial<FeedCard>): FeedCard => ({ ...agentSkabelon, ...o })
const udenSession = 'sess-oprindelse'

const FEJL = kort({
  ref_id: 'asg-fejl', assignment_id: 'asg-fejl', agent_id: 'a-fejl', title: 'researcher: Byg alt', section: 'venter',
  bucket: 'failed', reason: 'Fejlede (AGENT_FAILED, fase model)', origin_session_id: udenSession,
  error: { phase: 'model', code: 'AGENT_FAILED', reason: 'udbyder nede' }, can_acknowledge: true,
  state: { read: false, acknowledged: false, model_claim: 'accepted', assignment_status: 'failed' },
})
const UKENDT = kort({
  ref_id: 'asg-ukendt', assignment_id: 'asg-ukendt', agent_id: 'a-ukendt', title: 'researcher: Skriv til server',
  section: 'venter', bucket: 'outcome_unknown', origin_session_id: udenSession, reason: 'Udfaldet er ukendt – kræver afklaring før arbejdet fortsætter',
  can_acknowledge: false, error: null,
  state: { read: true, acknowledged: false, model_claim: '', assignment_status: 'waiting' },
})
const SVAR = kort({
  ref_id: 'asg-ok', assignment_id: 'asg-ok', agent_id: 'a-ok', title: 'researcher: Find kilder', section: 'svar',
  bucket: 'done', reason: '', summary: 'Tre kilder fundet i docs/', can_acknowledge: true, error: null,
  state: { read: false, acknowledged: false, model_claim: 'claimed_by_model_step', assignment_status: 'completed' },
})
const AKTIV = kort({
  ref_id: 'asg-go', assignment_id: 'asg-go', agent_id: 'a-go', title: 'researcher: Kører stadig', section: 'aktiv',
  bucket: 'active', reason: '', can_acknowledge: false, error: null,
  state: { read: false, acknowledged: false, model_claim: '', assignment_status: 'active' },
})
const APPROVAL = kort({
  ...approvalSkabelon, ref_id: 'appr-1', agent_id: 'a-fejl', assignment_id: 'asg-fejl', origin_session_id: udenSession,
  title: 'Godkend: bash', summary: 'bash({"command": "make"})',
  approval: { approval_id: 'appr-1', digest: 'dig-123', risk_class: 'write', expires_at: '2026-10-09T00:00:00Z', tool_name: 'bash', status: 'pending' },
})

const svarFeed = (cards: FeedCard[]) => ({ status: 'ok', cards, counts: { venter: 0, svar: 0, aktiv: 0, unread: 0 }, contract_version: 'agent-contract-v1' })

beforeEach(() => {
  hent.mockReset().mockResolvedValue({ poster: [], antal: 0, venter: 0 })
  hentHistorik.mockReset().mockResolvedValue({ poster: [], antal: 0 })
  feed.mockReset().mockResolvedValue(svarFeed([FEJL, UKENDT, SVAR, AKTIV, APPROVAL]))
  laest.mockReset().mockResolvedValue({ read: true })
  kvitter.mockReset().mockResolvedValue({ acknowledged: true })
  afgoer.mockReset().mockResolvedValue({ status: 'ok', approval: { status: 'approved' } })
  localStorage.clear()
  sockets.length = 0
})

describe('NotifikationsFeed — agentkort', () => {
  it('fejl, ukendt udfald og approval står under «Venter på dig»; succes under «Svar»', async () => {
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByTestId('notif-agent-asg-fejl')).toBeInTheDocument()
    expect(screen.getByTestId('notif-agent-asg-ukendt')).toBeInTheDocument()
    expect(screen.getByTestId('notif-agent-appr-1')).toBeInTheDocument()
    expect(screen.queryByTestId('notif-agent-asg-ok')).toBeNull()                       // succes er ikke «venter»
    expect(screen.getByRole('tab', { name: /Venter på dig/ })).toHaveTextContent('3')
    expect(screen.getByRole('tab', { name: /^Svar/ })).toHaveTextContent('1')            // kun succes tæller; «i gang» er ikke et svar
    fireEvent.click(screen.getByRole('tab', { name: /^Svar/ }))
    expect(await screen.findByTestId('notif-agent-asg-ok')).toBeInTheDocument()
    expect(screen.getByText('Agenter i gang (1)')).toBeInTheDocument()
    expect(screen.getByTestId('notif-agent-asg-go')).toBeInTheDocument()
    expect(screen.queryByTestId('notif-agent-asg-fejl')).toBeNull()
  })

  it('kortet viser årsag, fejlkode og et begrænset resumé — ikke agentens fulde output', async () => {
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByTestId('notif-agent-asg-fejl')
    expect(screen.getByText(/Fejlårsag: fase model · AGENT_FAILED · udbyder nede/)).toBeInTheDocument()
    expect(screen.getByTestId('ac-aarsag-asg-ukendt')).toHaveTextContent('Udfaldet er ukendt')
    fireEvent.click(screen.getByRole('tab', { name: /^Svar/ }))
    expect(await screen.findByTestId('ac-resume-asg-ok')).toHaveTextContent('Tre kilder fundet i docs/')
  })

  it('læst, kvitteret og modelclaim er adskilte tilstande på kortet', async () => {
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByTestId('notif-agent-asg-fejl')
    expect(screen.getByTestId('ac-tilstande-asg-fejl')).toHaveTextContent('Fejlet · ulæst · ikke kvitteret · modellen: ikke set af modellen endnu')
    expect(screen.getByTestId('ac-tilstande-asg-ukendt')).toHaveTextContent('Udfald ukendt · læst')
    expect(screen.getByTestId('ac-tilstande-asg-ukendt')).not.toHaveTextContent('kvitteret')
    fireEvent.click(screen.getByRole('tab', { name: /^Svar/ }))
    expect(await screen.findByTestId('ac-tilstande-asg-ok')).toHaveTextContent('Færdig · ulæst · ikke kvitteret · modellen: set af modellen')
  })

  it('klik åbner den OPRINDELIGE session + inspectoren (via onAabnAgent) og markerer læst — injicerer intet', async () => {
    const aabnAgent = vi.fn()
    const aabnSession = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabnSession} onAabnAgent={aabnAgent}
                              aktivSession="en-helt-anden-session" />)
    fireEvent.click(await screen.findByTestId('notif-agent-asg-fejl'))
    expect(aabnAgent).toHaveBeenCalledWith(expect.objectContaining({ agent_id: 'a-fejl', origin_session_id: udenSession }))
    expect(aabnSession).not.toHaveBeenCalled()
    await waitFor(() => expect(laest).toHaveBeenCalledWith(cfg, 'agent', 'asg-fejl'))
  })

  it('uden inspector-handler åbner kortet i det mindste den oprindelige session', async () => {
    const aabnSession = vi.fn()
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={aabnSession} />)
    fireEvent.click(await screen.findByTestId('notif-agent-asg-ukendt'))
    expect(aabnSession).toHaveBeenCalledWith(udenSession)
  })

  it('en approval afgøres med netop dens digest og totrinskode — og først da hentes feedet igen', async () => {
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    const k = await screen.findByTestId('notif-agent-appr-1')
    const rk = k.closest('li')!
    fireEvent.change(within(rk).getByLabelText('Totrinskode'), { target: { value: '123456' } })
    const foer = feed.mock.calls.length
    fireEvent.click(within(rk).getByRole('button', { name: 'Godkend' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, 'appr-1', 'approve', 'dig-123', '123456'))
    await waitFor(() => expect(feed.mock.calls.length).toBeGreaterThan(foer))
  })

  it('Afvis sender ingen kode, og en afvist godkendelse viser serverens grund', async () => {
    afgoer.mockRejectedValue(new Error('Godkendelsen er udløbet.'))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    const rk = (await screen.findByTestId('notif-agent-appr-1')).closest('li')!
    fireEvent.click(within(rk).getByRole('button', { name: 'Afvis' }))
    await waitFor(() => expect(afgoer).toHaveBeenCalledWith(cfg, 'appr-1', 'deny', 'dig-123', ''))
    expect(await screen.findByText('Godkendelsen er udløbet.')).toBeInTheDocument()
  })

  it('kun terminale kort kan kvitteres; en uafklaret skrivning har ingen kvitteringsknap', async () => {
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByTestId('notif-agent-asg-ukendt')
    expect(screen.queryByRole('button', { name: /^Kvittér researcher: Skriv til server/ })).toBeNull()
    fireEvent.click(screen.getByRole('button', { name: 'Kvittér researcher: Byg alt' }))
    await waitFor(() => expect(kvitter).toHaveBeenCalledWith(cfg, 'asg-fejl'))
  })

  it('en fejlet hentning af agentkort er IKKE «alt er klaret»', async () => {
    feed.mockRejectedValue(new Error('nede'))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByTestId('ac-feed-fejl')).toHaveTextContent('ukendt, ikke tom')
    expect(screen.getByText(/Kan ikke bekræfte at intet venter/)).toBeInTheDocument()
    expect(screen.queryByText('Ingen notifikationer — alt er klaret.')).toBeNull()
  })

  it('et notifikation.agent-signal henter agentkortene igen; et fremmed signal gør ikke', async () => {
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    await screen.findByTestId('notif-agent-asg-fejl')
    const foer = feed.mock.calls.length
    sockets[0]!.onmessage!({ data: JSON.stringify({ kind: 'runtime.noget-andet' }) })
    expect(feed.mock.calls.length).toBe(foer)
    sockets[0]!.onmessage!({ data: JSON.stringify({ kind: 'notifikation.agent', payload: { ref_id: 'asg-fejl' } }) })
    await waitFor(() => expect(feed.mock.calls.length).toBeGreaterThan(foer))
  })

  it('uden agentkort er feedet uændret «alt er klaret»', async () => {
    feed.mockResolvedValue(svarFeed([]))
    render(<NotifikationsFeed config={cfg} onLuk={() => {}} onAabnSession={() => {}} />)
    expect(await screen.findByText('Ingen notifikationer — alt er klaret.')).toBeInTheDocument()
  })
})
