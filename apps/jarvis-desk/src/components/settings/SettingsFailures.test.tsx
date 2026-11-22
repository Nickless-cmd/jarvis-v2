import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { McpSection } from './McpSection'
import { WorkbenchSection } from './WorkbenchSection'
import { PermissionsSection } from './PermissionsSection'
import * as api from '../../lib/coworkApi'
vi.mock('../../lib/coworkApi', () => ({
  getAccountMcp: vi.fn(), getMcpTrust: vi.fn(), addMcpServer: vi.fn(), removeMcpServer: vi.fn(),
  allowMcpServer: vi.fn(), revokeMcpServer: vi.fn(),
  // Markedspladsen (22/11-2026): McpSection henter kataloget i samme Promise.all
  // som listen og trust. Uden disse to i mocken er de `undefined`, kaldet kaster,
  // og HELE sektionen lander i fejl-tilstand — så testen nedenfor kunne hverken
  // se godkendelses-knappen eller komme videre efter «Prøv igen».
  getMcpCatalog: vi.fn(async () => [] as never), installMcpCatalogEntry: vi.fn(),
  getOperatorChannel: vi.fn(),
  getCheckpoints: vi.fn(), getRuntimeSwitches: vi.fn(), setOperatorChannel: vi.fn(),
  rollbackCheckpoint: vi.fn(), setRuntimeSwitch: vi.fn(),
  getAccountPermissions: vi.fn(), setComputerUse: vi.fn(),
}))
const config = { apiBaseUrl: 'http://test', authToken: 'test' }
beforeEach(() => vi.resetAllMocks())
describe('settings failures are not empty state', () => {
  it('keeps the confirmed permission when saving is rejected', async () => {
    vi.mocked(api.getAccountPermissions).mockResolvedValue({ role: 'owner', computer_use_enabled: false, modes: [] })
    vi.mocked(api.setComputerUse).mockRejectedValue(new Error('rejected'))
    render(<PermissionsSection config={config} />)
    const toggle = await screen.findByRole('checkbox', { name: 'Computer-use' })
    fireEvent.click(toggle)
    expect(await screen.findByRole('alert')).toHaveTextContent('Tilladelsen kunne ikke ændres')
    expect(toggle).not.toBeChecked()
    expect(toggle).toBeEnabled()
  })
  it('never offers approval when MCP trust cannot be read, then recovers on retry', async () => {
    vi.mocked(api.getAccountMcp).mockResolvedValue([{ id: 'x', name: 'Files', url: 'https://example.com' }] as never)
    vi.mocked(api.getMcpTrust).mockRejectedValueOnce(new Error('offline')).mockResolvedValue({ servere: [], pins: {} } as never)
    // Kataloget er en tredje parallel hentning (22/11-2026). Uden en returværdi
    // giver den `undefined`, og `Promise.all` fejler på den — så sektionen kan
    // aldrig komme ud af fejl-tilstanden, uanset at trust-kaldet lykkes anden gang.
    vi.mocked(api.getMcpCatalog).mockResolvedValue([] as never)
    render(<McpSection config={config} />)
    expect(await screen.findByRole('alert')).toHaveTextContent(/godkendelser/i)
    expect(screen.queryByText('ikke godkendt')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /^Godkend$/ })).not.toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Prøv igen' }))
    expect(await screen.findByRole('button', { name: /^Godkend$/ })).toBeEnabled()
  })
  it('does not claim channel is closed or checkpoints empty after failed requests', async () => {
    vi.mocked(api.getOperatorChannel).mockRejectedValue(new Error('offline'))
    vi.mocked(api.getCheckpoints).mockRejectedValue(new Error('offline'))
    vi.mocked(api.getRuntimeSwitches).mockRejectedValue(new Error('offline'))
    render(<WorkbenchSection config={config} />)
    await waitFor(() => expect(screen.getAllByRole('alert')).toHaveLength(3))
    expect(screen.queryByText(/Lukket —/)).not.toBeInTheDocument()
    expect(screen.queryByText(/Intet at fortryde/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Åbn' })).not.toBeInTheDocument()
  })
})
