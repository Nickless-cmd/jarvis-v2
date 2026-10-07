import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent, within } from '@testing-library/react'
import fixture from '../../lib/__fixtures__/agentContract.json'
import type { ContractAgentRow, ContractOverview } from '../../lib/agentContractApi'

const listJobs = vi.fn()
vi.mock('../../lib/jobsApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/jobsApi')>('../../lib/jobsApi')
  return { ...rigtig, listJobs: (...a: unknown[]) => listJobs(...a), stopJob: vi.fn() }
})
const overblik = vi.fn()
const stop = vi.fn()
const kvitter = vi.fn()
vi.mock('../../lib/agentContractApi', async () => {
  const rigtig = await vi.importActual<typeof import('../../lib/agentContractApi')>('../../lib/agentContractApi')
  return {
    ...rigtig,
    getKontraktOverblik: (...a: unknown[]) => overblik(...a),
    kontraktStop: (...a: unknown[]) => stop(...a),
    kvitterKontrakt: (...a: unknown[]) => kvitter(...a),
  }
})

import { JobsPanel } from './JobsPanel'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
// Rækkeformen er den RIGTIGE rute-respons (se agentContractApi.test.ts for feltnavne-pinningen).
const skabelon = fixture.overview.agents[0] as unknown as ContractAgentRow
const raekke = (o: Partial<ContractAgentRow>): ContractAgentRow => ({ ...skabelon, council_id: '', ...o })

const KOERER = raekke({ agent_id: 'a-koerer', goal: 'Undersøg logs', bucket: 'active', assignment_status: 'active', duration_s: 75, attention: false })
const KOE = raekke({ agent_id: 'a-koe', assignment_id: 'asg-koe', goal: 'Vent i kø', bucket: 'queued', assignment_status: 'queued', run_status: 'queued', attention: false, duration_s: 3 })
const GODKEND = raekke({ agent_id: 'a-godkend', assignment_id: 'asg-g', goal: 'Slet build', bucket: 'waiting_for_approval', assignment_status: 'waiting', attention: true, reason: 'Venter på din godkendelse', duration_s: 10 })
const UKENDT = raekke({ agent_id: 'a-ukendt', assignment_id: 'asg-u', goal: 'Skriv til server', bucket: 'outcome_unknown', assignment_status: 'waiting', attention: true, reason: 'Udfaldet er ukendt – kræver afklaring før arbejdet fortsætter', duration_s: 40 })
const FEJLET = raekke({
  agent_id: 'a-fejl', assignment_id: 'asg-f', goal: 'Byg alt', bucket: 'failed', assignment_status: 'failed', attention: true,
  reason: 'Fejlede (AGENT_FAILED, fase model)', error: { phase: 'model', code: 'AGENT_FAILED', reason: 'udbyder nede' }, duration_s: 12,
})

const svar = (agents: ContractAgentRow[], groups: ContractOverview['groups'] = []): ContractOverview => ({
  status: 'ok', agents, groups, contract_version: 'agent-contract-v1',
  capability: { enabled: true, reason: '', contract_version: 'agent-contract-v1' },
  counts: {
    active: agents.filter((a) => a.bucket === 'active').length, queued: 0, waiting: 0, blocked: 0,
    attention: agents.filter((a) => a.attention).length, open: agents.length,
  },
})

beforeEach(() => {
  listJobs.mockReset().mockResolvedValue({ jobs: [], bridge_ok: true })
  overblik.mockReset().mockResolvedValue(svar([KOERER, KOE, GODKEND, UKENDT, FEJLET]))
  stop.mockReset().mockResolvedValue({ receipt: { kind: 'stop', accepted: true, confirmed: false, code: '', state: 'stop_requested', delivered: null } })
  kvitter.mockReset().mockResolvedValue({ acknowledged: true })
})

describe('JobsPanel — agentrun fra kontrakten', () => {
  it('én logisk række pr. agentrun, med opgave, rolle, target, status og varighed', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    const r = await screen.findByTestId('ac-job-a-koerer')
    expect(within(r).getByText('Undersøg logs')).toBeInTheDocument()
    expect(within(r).getByText('researcher')).toBeInTheDocument()
    expect(within(r).getByText('container')).toBeInTheDocument()
    expect(within(r).getByText('Kører')).toBeInTheDocument()
    expect(within(r).getByText('1m 15s')).toBeInTheDocument()
    expect(overblik).toHaveBeenCalledWith(cfg, 'panel')
    expect(screen.getAllByTestId(/^ac-job-/)).toHaveLength(5)
  })

  it('tælleren for det der kører er ADSKILT fra opmærksomhedslisten', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByTestId('ac-job-a-koerer')
    expect(screen.getByTestId('ac-koerer-tal')).toHaveTextContent('2')                   // kører + kø
    const hoved = screen.getByTestId('ac-opmaerksomhed')
    expect(hoved).toHaveTextContent('Kræver opmærksomhed')
    expect(hoved).toHaveTextContent('3')                                                  // godkendelse, ukendt, fejlet
    // opmærksomhedsrækker står IKKE i «Kører»
    const koerer = screen.getByTestId('ac-koerer-tal').closest('div')!.nextElementSibling as HTMLElement
    expect(within(koerer).queryByTestId('ac-job-a-fejl')).toBeNull()
    expect(within(koerer).getByTestId('ac-job-a-koe')).toBeInTheDocument()
  })

  it('ventetilstande, ukendt udfald og fejl forbliver synlige med årsag og mulig handling', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    const g = await screen.findByTestId('ac-job-a-godkend')
    expect(within(g).getByText('Venter på din godkendelse', { selector: '.ac-aarsag' })).toBeInTheDocument()
    expect(within(g).getByRole('button', { name: /^Stop agent/ })).toBeInTheDocument()   // åbent -> kan stoppes
    const u = screen.getByTestId('ac-job-a-ukendt')
    expect(within(u).getByText(/Udfaldet er ukendt/)).toBeInTheDocument()
    const f = screen.getByTestId('ac-job-a-fejl')
    expect(within(f).getByText(/udbyder nede/)).toBeInTheDocument()
    expect(within(f).queryByRole('button', { name: /^Stop agent/ })).toBeNull()          // terminal: kvittér, ikke stop
    expect(within(f).getByRole('button', { name: /^Kvittér/ })).toBeInTheDocument()
  })

  it('en kø-række vises som ventende, ikke som kørende', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    const k = await screen.findByTestId('ac-job-a-koe')
    expect(k).toHaveAttribute('data-bucket', 'queued')
    expect(within(k).getByText('I kø')).toBeInTheDocument()
  })

  it('klik på en række åbner inspectoren for netop den agent', async () => {
    const aabn = vi.fn()
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} onOpenAgent={aabn} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Åbn agent Slet build' }))
    expect(aabn).toHaveBeenCalledWith({ agentId: 'a-godkend', role: skabelon.role, goal: 'Slet build',
      status: 'waiting_for_approval', dispatchToolUseId: '' })
  })

  it('Stop bruger kontrakt-ruten og viser en ACCEPT-besked — ikke «stoppet»', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Stop agent Undersøg logs' }))
    await waitFor(() => expect(stop).toHaveBeenCalledWith(cfg, 'a-koerer'))
    expect(await screen.findByText(/Stop anmodet.*ikke bekræftet/)).toBeInTheDocument()
  })

  it('en almindelig bruger (ikke owner) kan stoppe sin EGEN agent — serveren afgør ejerskabet', async () => {
    render(<JobsPanel config={cfg} isOwner={false} onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Stop agent Undersøg logs' }))
    await waitFor(() => expect(stop).toHaveBeenCalled())
  })

  it('en afvist stop viser serverens grund', async () => {
    stop.mockRejectedValue(new Error('Agenten findes ikke for dig.'))
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    fireEvent.click(await screen.findByRole('button', { name: 'Stop agent Undersøg logs' }))
    expect(await screen.findByText('Agenten findes ikke for dig.')).toBeInTheDocument()
  })

  it('kvittering af en fejl kalder serveren med assignment-id; først derefter forsvinder den', async () => {
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    overblik.mockResolvedValue(svar([KOERER, KOE, GODKEND, UKENDT]))                    // serveren har nu kvitteret
    fireEvent.click(await screen.findByRole('button', { name: 'Kvittér Byg alt' }))
    await waitFor(() => expect(kvitter).toHaveBeenCalledWith(cfg, 'asg-f'))
    await waitFor(() => expect(screen.queryByTestId('ac-job-a-fejl')).toBeNull())
  })

  it('succes optræder ikke i panelet (serveren sender den ikke) — og ingen række opfindes', async () => {
    overblik.mockResolvedValue(svar([KOERER]))
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByTestId('ac-job-a-koerer')
    expect(screen.queryByTestId('ac-opmaerksomhed')).toBeNull()
    expect(screen.getAllByTestId(/^ac-job-/)).toHaveLength(1)
  })

  it('en fejlet kontrakt-hentning er IKKE en tom agentliste', async () => {
    overblik.mockRejectedValue(new Error('nede'))
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    expect(await screen.findByText(/Agent-kontrakten kunne ikke hentes/)).toBeInTheDocument()
    expect(screen.getByText('Ingenting kører lige nu.')).toBeInTheDocument()            // jobs-listen er stadig sin egen
  })

  it('listen og tælleren kommer fra kontrakten selv når klientbroen er nede', async () => {
    listJobs.mockResolvedValue({ jobs: [], bridge_ok: false })
    const antal = vi.fn()
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} onCount={antal} />)
    await screen.findByTestId('ac-job-a-koerer')
    expect(screen.getByText(/Kan ikke se din maskine/)).toBeInTheDocument()
    await waitFor(() => expect(antal).toHaveBeenLastCalledWith(2))
  })

  it('en kontrakt-agent står ikke to gange (scout-rækken fra /api/jobs fjernes)', async () => {
    listJobs.mockResolvedValue({
      jobs: [
        { id: 'a-koerer', kilde: 'agent', navn: 'Undersøg logs', kommando: 'Scout-agent', status: 'running', sekunder: 80, exit_code: null },
        { id: 'gammel-scout', kilde: 'agent', navn: 'Gammel scout', kommando: 'Scout-agent', status: 'running', sekunder: 9, exit_code: null },
      ], bridge_ok: true,
    })
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    await screen.findByTestId('ac-job-a-koerer')
    expect(await screen.findByText('Gammel scout')).toBeInTheDocument()                 // uden kontrakt: vises som før
    expect(screen.getAllByText('Undersøg logs')).toHaveLength(1)
    expect(screen.getByTestId('ac-koerer-tal')).toHaveTextContent('3')                  // 2 kontrakt + 1 gammel scout
  })

  it('et råd vises som en gruppering af almindelige rækker med medlemsstatus og syntese', async () => {
    const m1 = raekke({ agent_id: 'm1', assignment_id: 'asg-m1', goal: 'Vurdering A', role: 'member', council_id: 'raad-7', bucket: 'active', attention: false })
    const m2 = raekke({ agent_id: 'm2', assignment_id: 'asg-m2', goal: 'Vurdering B', role: 'member', council_id: 'raad-7', bucket: 'queued', attention: false })
    const syn = raekke({ agent_id: 'syn', assignment_id: 'asg-s', goal: 'Syntese', role: 'synthesis', council_id: 'raad-7', bucket: 'queued', attention: false })
    overblik.mockResolvedValue(svar([m1, m2, syn], [{
      council_id: 'raad-7', members: [{ agent_id: 'm1', role: 'member', bucket: 'active' }, { agent_id: 'm2', role: 'member', bucket: 'queued' }],
      synthesis: { agent_id: 'syn', bucket: 'queued' },
      counts: { active: 1, queued: 2, waiting: 0, blocked: 0, attention: 0, open: 3 },
    }]))
    render(<JobsPanel config={cfg} isOwner onClose={() => {}} />)
    const hoved = await screen.findByTestId('ac-raad-raad-7')
    expect(hoved).toHaveTextContent('Råd raad-7 · 3 rækker · syntese: I kø')
    expect(screen.getAllByTestId(/^ac-job-/)).toHaveLength(3)                           // stadig én række pr. run
  })
})
