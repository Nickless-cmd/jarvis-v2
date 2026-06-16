import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

const getConnectors = vi.fn()
const startConnect = vi.fn().mockResolvedValue('https://github.com/login/oauth/authorize?x')
vi.mock('../../lib/connectorsApi', () => ({
  getConnectors: (...a: unknown[]) => getConnectors(...a),
  startConnect: (...a: unknown[]) => startConnect(...a),
}))

import { GreetingHero } from './GreetingHero'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
const oauthC = (id: string, connected: boolean) => ({
  id, name: id, kind: 'oauth', category: 'x', icon: id, desc: 'd', scopes: ['s'], post_connect_hint: null, connected, enabled: true,
})

describe('GreetingHero', () => {
  beforeEach(() => { getConnectors.mockReset(); startConnect.mockClear()
    ;(window as unknown as { jarvisDesk: { openExternal: ReturnType<typeof vi.fn> } }).jarvisDesk = { openExternal: vi.fn().mockResolvedValue(undefined) }
  })

  it('viser greeting (hilsen) + composer-slot', () => {
    getConnectors.mockResolvedValue([])
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}}>composer</GreetingHero>)
    expect(screen.getByText(/Bjørn/)).toBeInTheDocument()
    expect(screen.getByText('composer')).toBeInTheDocument()
  })

  it('viser kun ikke-forbundne oauth-connectors (max 3)', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false), oauthC('gmail', false), oauthC('cal', false), oauthC('drive', false), oauthC('done', true)])
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}}>c</GreetingHero>)
    await waitFor(() => expect(screen.getByText('github')).toBeInTheDocument())
    expect(screen.queryByText('done')).not.toBeInTheDocument()
    expect(screen.queryByText('drive')).not.toBeInTheDocument() // 4. forslag klippes
  })

  it('Flere apps → kalder onOpenMarketplace', async () => {
    getConnectors.mockResolvedValue([])
    const onOpen = vi.fn()
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={onOpen}>c</GreetingHero>)
    fireEvent.click(screen.getByText(/Flere apps/i))
    expect(onOpen).toHaveBeenCalled()
  })

  it('Forbind kalder startConnect + openExternal', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false)])
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}}>c</GreetingHero>)
    await waitFor(() => expect(screen.getByText('Forbind')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Forbind'))
    await waitFor(() => expect(startConnect).toHaveBeenCalledWith(cfg, 'github'))
  })
})
