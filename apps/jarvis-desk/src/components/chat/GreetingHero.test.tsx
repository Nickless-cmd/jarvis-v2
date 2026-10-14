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
    render(<GreetingHero config={cfg} userName="Bjørn">composer</GreetingHero>)
    expect(screen.getByText(/Bjørn/)).toBeInTheDocument()
    expect(screen.getByText('composer')).toBeInTheDocument()
  })

  // 13/10-2026: sol/måne-glyphen er væk — hilsenen er ren tekst.
  it('tegner ingen sol/måne-glyph', () => {
    getConnectors.mockResolvedValue([])
    render(<GreetingHero config={cfg} userName="Bjørn">c</GreetingHero>)
    expect(screen.queryByText(/🌅|☀️|🌆|🌙/)).not.toBeInTheDocument()
  })

  it('viser kun IKKE-forbundne apps, Gmail først, max 3 — forbundne forsvinder', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false), oauthC('gmail', false), oauthC('cal', false), oauthC('drive', false), oauthC('slack', true)])
    render(<GreetingHero config={cfg} userName="Bjørn">c</GreetingHero>)
    await waitFor(() => expect(screen.getByText('gmail')).toBeInTheDocument())
    // «slack» er forbundet → sat op én gang → væk fra rækken. Kun 3 vises.
    const names = screen.getAllByText(/^(github|gmail|cal|drive|slack)$/).map((n) => n.textContent)
    expect(names[0]).toBe('gmail') // Gmail først
    expect(names.length).toBe(3)
    expect(screen.queryByText('slack')).not.toBeInTheDocument()
  })

  it('har ingen «Flere apps»-knap — opsætningen hører i Marketplace', async () => {
    // 13/10-2026 (Bjørn): «flere apps skal væk». Rækken viser de apps der
    // mangler at blive sat op; resten hører i Marketplace, ikke på tom-skærmen.
    getConnectors.mockResolvedValue([])
    render(<GreetingHero config={cfg} userName="Bjørn">c</GreetingHero>)
    await waitFor(() => expect(screen.queryByText(/Flere apps/i)).not.toBeInTheDocument())
  })

  it('post-connect-hint: viser chip + Ja tak kalder onSuggest', async () => {
    getConnectors.mockResolvedValue([])
    localStorage.setItem('jarvis-desk:post-connect-hint', 'Nu kan jeg kigge i dine GitHub-issues — skal jeg?')
    const onSuggest = vi.fn()
    render(<GreetingHero config={cfg} userName="Bjørn" onSuggest={onSuggest}>c</GreetingHero>)
    expect(screen.getByText(/GitHub-issues/)).toBeInTheDocument()
    fireEvent.click(screen.getByText('Ja tak'))
    expect(onSuggest).toHaveBeenCalledWith('Nu kan jeg kigge i dine GitHub-issues — skal jeg?')
  })

  it('klik på en app-pille kalder startConnect + openExternal', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false)])
    render(<GreetingHero config={cfg} userName="Bjørn">c</GreetingHero>)
    fireEvent.click(await screen.findByTitle('Forbind github'))
    await waitFor(() => expect(startConnect).toHaveBeenCalledWith(cfg, 'github'))
  })

  it('opens connector authorization from the browser greeting', async () => {
    getConnectors.mockResolvedValue([oauthC('github', false)])
    ;(window as Window & { jarvisDesk?: unknown }).jarvisDesk = undefined
    const popup = { opener: window, location: { href: '' }, close: vi.fn() }
    const open = vi.fn(() => popup)
    vi.stubGlobal('open', open)
    render(<GreetingHero config={cfg} userName="Bjørn">c</GreetingHero>)
    fireEvent.click(await screen.findByTitle('Forbind github'))
    expect(open).toHaveBeenCalledWith('about:blank', '_blank')
    await waitFor(() => expect(popup.location.href).toBe('https://github.com/login/oauth/authorize?x'))
    vi.unstubAllGlobals()
  })
})
