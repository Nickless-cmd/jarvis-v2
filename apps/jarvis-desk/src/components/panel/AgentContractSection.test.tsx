import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { AgentInspector } from './AgentInspector'
import * as pool from '../../lib/agentPoolApi'
import * as kontrakt from '../../lib/agentContractApi'
import type { ContractDetail } from '../../lib/agentContractApi'
import fixture from '../../lib/__fixtures__/agentContract.json'

const config = { apiBaseUrl: 'http://x', authToken: 't' }
const ref = { agentId: 'agent-a', role: 'researcher', goal: 'find X', status: 'active', dispatchToolUseId: '' }
// Den RIGTIGE rute-respons (genereret af backend-testen) — ikke en opfundet form.
const live = fixture.detail as unknown as ContractDetail
const med = (patch: Partial<ContractDetail['agent']>, rest: Partial<ContractDetail> = {}): ContractDetail =>
  ({ ...live, ...rest, agent: { ...live.agent, ...patch } })

beforeEach(() => {
  vi.restoreAllMocks()
  vi.spyOn(pool, 'getAgentDetalje').mockResolvedValue({
    agent_id: 'agent-a', role: 'researcher', goal: 'find X', status: 'active', runs: [], messages: [],
  })
  vi.spyOn(kontrakt, 'getKontraktAgent').mockResolvedValue(live)
})

describe('AgentInspector — kontrakt-visning', () => {
  it('viser status, target, heartbeat, rute, omkostning og seneste forsøg fra projektionen', async () => {
    render(<AgentInspector config={config} agent={ref} canMessage />)
    const facts = await screen.findByTestId('ac-status')
    expect(within(facts).getByText('Kører')).toHaveAttribute('data-bucket', 'active')
    expect(within(facts).getByText('container')).toBeInTheDocument()
    expect(within(facts).getByText(/levende/)).toBeInTheDocument()
    expect(within(facts).getByText(/agent_pool · p\/m/)).toBeInTheDocument()
    expect(within(facts).getByText('ikke meldt')).toBeInTheDocument()        // ingen forbrug: «ingen data» ≠ «gratis»
    expect(within(facts).getByText('agent-kid')).toBeInTheDocument()          // agenttræet: børn
  })

  it('en ventende approval vises med sikker visning og henviser til «Venter på dig»', async () => {
    render(<AgentInspector config={config} agent={ref} canMessage />)
    await screen.findByTestId('ac-status')
    expect(screen.getByText(/Venter på godkendelse:/)).toBeInTheDocument()
    expect(screen.getByText(/bash\(/)).toBeInTheDocument()
    expect(screen.getByText(/Venter på dig/)).toBeInTheDocument()
  })

  it('fejlårsagen vises med fase, kode og årsag — og en fejlet agent kan ikke stoppes, kun følges op', async () => {
    vi.mocked(kontrakt.getKontraktAgent).mockResolvedValue(med({
      bucket: 'failed', attention: true, assignment_status: 'failed',
      error: { phase: 'model', code: 'AGENT_FAILED', reason: 'udbyderen svarede ikke' },
    }))
    render(<AgentInspector config={config} agent={ref} canMessage />)
    expect(await screen.findByTestId('ac-error')).toHaveTextContent('fase model · AGENT_FAILED · udbyderen svarede ikke')
    expect(screen.getByText(/kræver opmærksomhed/)).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
    expect(screen.getByRole('textbox', { name: 'Opfølgning til agenten' })).toBeInTheDocument()
  })

  it('outcome_unknown siger højt at handlingen kan være udført og ikke gentages', async () => {
    vi.mocked(kontrakt.getKontraktAgent).mockResolvedValue(med({
      bucket: 'outcome_unknown', attention: true, assignment_status: 'waiting', run_status: 'outcome_unknown',
      reason: 'Udfaldet er ukendt – kræver afklaring før arbejdet fortsætter',
    }))
    render(<AgentInspector config={config} agent={ref} canMessage />)
    expect(await screen.findByRole('alert')).toHaveTextContent('Udfaldet er ukendt')
    expect(screen.getByText('Udfald ukendt · kræver opmærksomhed')).toBeInTheDocument()
  })

  it('Stop giver en ACCEPT-kvittering, aldrig «stoppet» — først projektionen bekræfter', async () => {
    const stop = vi.spyOn(kontrakt, 'kontraktStop').mockResolvedValue(fixture.stop as never)
    const user = userEvent.setup()
    render(<AgentInspector config={config} agent={ref} canMessage />)
    await screen.findByTestId('ac-status')
    await user.click(await screen.findByRole('button', { name: 'Stop' }))
    expect(stop).toHaveBeenCalledWith(config, 'agent-a')
    const kvit = await screen.findByTestId('ac-receipt')
    expect(kvit).toHaveTextContent('Stop er anmodet. Agenten er ikke bekræftet stoppet endnu.')
    expect(kvit).toHaveTextContent('Registreret i databasen: nej')
    // Projektionen siger nu at assignmentet er afbrudt → først DA er det bekræftet. Stop-handlingen genindlæser
    // detaljen; det næste svar er det der afgør.
    vi.mocked(kontrakt.getKontraktAgent).mockResolvedValue(
      med({ assignment_status: 'cancelled', bucket: 'cancelled', attention: true }))
    await user.click(screen.getByRole('button', { name: 'Stop' }))
    await waitFor(() => expect(screen.getByTestId('ac-receipt')).toHaveTextContent('Registreret i databasen: ja'))
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
  })

  it('en besked kvitteres som accepteret og gemt — levering er ikke bekræftet', async () => {
    const send = vi.spyOn(kontrakt, 'kontraktBesked').mockResolvedValue(fixture.message as never)
    const user = userEvent.setup()
    render(<AgentInspector config={config} agent={ref} canMessage />)
    await screen.findByTestId('ac-status')
    const input = await screen.findByRole('textbox', { name: 'Besked til agenten' })
    await user.type(input, 'tag den røde vej')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(send).toHaveBeenCalledWith(config, 'agent-a', 'tag den røde vej'))
    expect(await screen.findByTestId('ac-receipt')).toHaveTextContent('Levering er ikke bekræftet')
    await waitFor(() => expect(input).toHaveValue(''))
  })

  it('en afvist besked bevarer kladden og viser serverens årsag', async () => {
    vi.spyOn(kontrakt, 'kontraktBesked').mockRejectedValue(new Error('Afvist af serveren: agent-kontrakten er slukket'))
    const user = userEvent.setup()
    render(<AgentInspector config={config} agent={ref} canMessage />)
    await screen.findByTestId('ac-status')
    const input = await screen.findByRole('textbox', { name: 'Besked til agenten' })
    await user.type(input, 'hej')
    await user.click(screen.getByRole('button', { name: 'Send' }))
    expect(await screen.findByText(/agent-kontrakten er slukket/)).toBeInTheDocument()
    expect(input).toHaveValue('hej')
    expect(screen.queryByTestId('ac-receipt')).not.toBeInTheDocument()
  })

  it('fuldt output åbnes via artefakten; en manglende/beskadiget/udløbet fil får en præcis tekst', async () => {
    const les = vi.spyOn(kontrakt, 'laesArtefakt')
    les.mockResolvedValueOnce({ status: 'ok', ref: 'r/final.txt', content: 'det fulde svar', truncated: false })
    const user = userEvent.setup()
    render(<AgentInspector config={config} agent={ref} canMessage />)
    await user.click(await screen.findByRole('button', { name: 'final.txt' }))
    expect(await screen.findByText('det fulde svar')).toBeInTheDocument()
    expect(les).toHaveBeenCalledWith(config, 'agent-a', expect.stringMatching(/^run-/), 'final.txt')
    for (const [status, tekst] of [['CORRUPT', /beskadiget/], ['MISSING', /mangler på disken/], ['EXPIRED', /udløbet/],
      ['NOT_FOUND', /findes ikke for dig/]] as const) {
      les.mockResolvedValueOnce({ status, ref: 'r/final.txt' })
      await user.click(screen.getByRole('button', { name: 'final.txt' }))
      expect(await within(screen.getByTestId('ac-artifact')).findByText(tekst)).toBeInTheDocument()
    }
  })

  it('mens det er uafgjort om agenten har en kontrakt, tilbydes de GAMLE styreknapper ikke', async () => {
    let frigiv: (v: ContractDetail | null) => void = () => {}
    vi.mocked(kontrakt.getKontraktAgent).mockReturnValue(new Promise((res) => { frigiv = res }))
    const cancel = vi.spyOn(pool, 'agentHandling')
    render(<AgentInspector config={config} agent={ref} canMessage />)
    await waitFor(() => expect(pool.getAgentDetalje).toHaveBeenCalled())
    await new Promise((r) => setTimeout(r, 20))
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Luk som udløbet' })).not.toBeInTheDocument()
    frigiv(null)                                         // ingen kontrakt -> nu (og først nu) vises den gamle visning
    expect(await screen.findByRole('button', { name: 'Luk som udløbet' })).toBeInTheDocument()
    expect(cancel).not.toHaveBeenCalled()
  })

  it('uden ret til at skrive (canMessage=false) vises ingen styring', async () => {
    render(<AgentInspector config={config} agent={ref} canMessage={false} />)
    await screen.findByTestId('ac-status')
    expect(screen.queryByRole('button', { name: 'Stop' })).not.toBeInTheDocument()
    expect(screen.queryByRole('textbox', { name: 'Besked til agenten' })).not.toBeInTheDocument()
  })

  it('bærer kontrakten alene, når den gamle MC-detalje afvises (en almindelig brugers egen agent)', async () => {
    vi.mocked(pool.getAgentDetalje).mockRejectedValue(new Error('HTTP 403'))
    render(<AgentInspector config={config} agent={ref} canMessage />)
    expect(await screen.findByTestId('ac-status')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('en fejlet kontraktvisning er en fejl, ikke tavshed — og den gamle visning består', async () => {
    vi.mocked(kontrakt.getKontraktAgent).mockRejectedValue(new Error('serveren er nede'))
    render(<AgentInspector config={config} agent={ref} canMessage />)
    expect(await screen.findByText('serveren er nede')).toBeInTheDocument()
    expect(screen.queryByTestId('ac-status')).not.toBeInTheDocument()
    expect(screen.getByText('Kørsler', { selector: '.inspector-kicker' })).toBeInTheDocument()
  })

  it('slukket kontrakt oplyses ved styringen', async () => {
    vi.mocked(kontrakt.getKontraktAgent).mockResolvedValue(
      { ...live, capability: { enabled: false, reason: 'kill switch', contract_version: 'agent-contract-v1' } })
    render(<AgentInspector config={config} agent={ref} canMessage />)
    expect(await screen.findByText(/Agent-kontrakten er slukket/)).toBeInTheDocument()
  })
})
