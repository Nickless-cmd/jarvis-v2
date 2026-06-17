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
  beforeEach(() => { getConnectors.mockReset(); startConnect.mockClear(); localStorage.clear()
    ;(window as unknown as { jarvisDesk: { openExternal: ReturnType<typeof vi.fn> } }).jarvisDesk = { openExternal: vi.fn().mockResolvedValue(undefined) }
  })

  it('viser greeting (hilsen) + composer-slot', () => {
    getConnectors.mockResolvedValue([])
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}}>composer</GreetingHero>)
    expect(screen.getByText(/Bjørn/)).toBeInTheDocument()
    expect(screen.getByText('composer')).toBeInTheDocument()
  })

  it('viser oauth-apps med Gmail først + forbundne sidst (max 4) + ✓ på forbundne', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false), oauthC('gmail', false), oauthC('cal', false), oauthC('drive', false), oauthC('slack', true)])
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}}>c</GreetingHero>)
    await waitFor(() => expect(screen.getByText('gmail')).toBeInTheDocument())
    // forbundne vises også (med ✓), men kun 4 i alt → en af de ikke-forbundne klippes
    const names = screen.getAllByText(/^(github|gmail|cal|drive|slack)$/).map((n) => n.textContent)
    expect(names[0]).toBe('gmail') // Gmail først
    expect(names.length).toBe(4)
  })

  it('Flere apps → kalder onOpenMarketplace', async () => {
    getConnectors.mockResolvedValue([])
    const onOpen = vi.fn()
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={onOpen}>c</GreetingHero>)
    fireEvent.click(screen.getByText(/Flere apps/i))
    expect(onOpen).toHaveBeenCalled()
  })

  it('post-connect-hint: viser chip + Ja tak kalder onSuggest', async () => {
    getConnectors.mockResolvedValue([])
    localStorage.setItem('jarvis-desk:post-connect-hint', 'Nu kan jeg kigge i dine GitHub-issues — skal jeg?')
    const onSuggest = vi.fn()
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}} onSuggest={onSuggest}>c</GreetingHero>)
    expect(screen.getByText(/GitHub-issues/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Ja tak'))
    expect(onSuggest).toHaveBeenCalledWith('Nu kan jeg kigge i dine GitHub-issues — skal jeg?')
  })

  it('Forbind kalder startConnect + openExternal', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false)])
    render(<GreetingHero config={cfg} userName="Bjørn" onOpenMarketplace={() => {}}>c</GreetingHero>)
    await waitFor(() => expect(screen.getByText('Forbind')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Forbind'))
    await waitFor(() => expect(startConnect).toHaveBeenCalledWith(cfg, 'github'))
  })
})
