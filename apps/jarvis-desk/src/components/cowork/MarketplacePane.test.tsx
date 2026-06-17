import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getConnectors = vi.fn()
const setEnabled = vi.fn().mockResolvedValue(undefined)
const deleteConnector = vi.fn().mockResolvedValue(undefined)
const startConnect = vi.fn().mockResolvedValue('https://github.com/login/oauth/authorize?x')
vi.mock('../../lib/connectorsApi', () => ({
  getConnectors: (...a: unknown[]) => getConnectors(...a),
  setEnabled: (...a: unknown[]) => setEnabled(...a),
  deleteConnector: (...a: unknown[]) => deleteConnector(...a),
  startConnect: (...a: unknown[]) => startConnect(...a),
}))

import { MarketplacePane } from './MarketplacePane'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const github = { id: 'github', name: 'GitHub', kind: 'oauth', category: 'Udvikling', icon: 'github', desc: 'Issues, PRs', scopes: ['repo', 'read:user'], post_connect_hint: 'hint', connected: false, enabled: true }
const computer = { id: 'computer-use', name: 'Computer Use', kind: 'local', category: 'System', icon: 'command', desc: 'Styr', scopes: [], post_connect_hint: null, connected: true, enabled: true }

describe('MarketplacePane', () => {
  beforeEach(() => { getConnectors.mockReset(); setEnabled.mockClear(); deleteConnector.mockClear(); startConnect.mockClear()
    ;(window as unknown as { jarvisDesk: { openExternal: ReturnType<typeof vi.fn> } }).jarvisDesk = { openExternal: vi.fn().mockResolvedValue(undefined) }
  })

  it('viser forbundet-sektion + alle connectors', async () => {
    getConnectors.mockResolvedValue([github, computer])
    render(<MarketplacePane config={cfg} />)
    await waitFor(() => expect(screen.getByText('GitHub')).toBeInTheDocument())
    expect(screen.getByText('Computer Use')).toBeInTheDocument()
    expect(screen.getByText(/Forbundet/i)).toBeInTheDocument()
  })

  it('viser scopes for oauth-connector', async () => {
    getConnectors.mockResolvedValue([github])
    render(<MarketplacePane config={cfg} />)
    await waitFor(() => expect(screen.getByText(/repo, read:user/)).toBeInTheDocument())
  })

  it('klik Forbind kalder startConnect + openExternal', async () => {
    getConnectors.mockResolvedValue([github])
    render(<MarketplacePane config={cfg} />)
    await waitFor(() => expect(screen.getByText('Forbind')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Forbind'))
    await waitFor(() => expect(startConnect).toHaveBeenCalledWith(cfg, 'github'))
    const bridge = (window as unknown as { jarvisDesk: { openExternal: ReturnType<typeof vi.fn> } }).jarvisDesk
    await waitFor(() => expect(bridge.openExternal).toHaveBeenCalled())
  })

  it('coming_soon vises med badge og uden Forbind-knap', async () => {
    const gmail = { id: 'gmail', name: 'Gmail', kind: 'oauth', category: 'Google', icon: 'mail', desc: 'Mails', scopes: ['gmail.send'], post_connect_hint: null, status: 'coming_soon', connected: false, enabled: true }
    getConnectors.mockResolvedValue([github, gmail])
    render(<MarketplacePane config={cfg} />)
    await waitFor(() => expect(screen.getByText('Gmail')).toBeInTheDocument())
    expect(screen.getAllByText(/Kommer snart/i).length).toBeGreaterThan(0)
    // github (available) har stadig Forbind; gmail har det ikke.
    expect(screen.getAllByText('Forbind')).toHaveLength(1)
  })

  it('⋯ → afbryd & slet (to-trins bekræft) kalder deleteConnector', async () => {
    getConnectors.mockResolvedValue([{ ...github, connected: true }, computer])
    render(<MarketplacePane config={cfg} />)
    await waitFor(() => expect(screen.getByText('GitHub')).toBeInTheDocument())
    // github er først i connected-sektionen → [0] er dens ⋯-menu.
    fireEvent.click(screen.getAllByLabelText('Mere')[0]!)
    fireEvent.click(screen.getByText(/Afbryd & slet/i))      // 1. klik = bekræft-trin
    fireEvent.click(screen.getByText(/Sikker\? Slet token/i)) // 2. klik = slet
    await waitFor(() => expect(deleteConnector).toHaveBeenCalledWith(cfg, 'github'))
  })
})
