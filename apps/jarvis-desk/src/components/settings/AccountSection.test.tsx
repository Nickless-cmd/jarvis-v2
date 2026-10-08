import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'

const getAccountMe = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAccountMe: (...a: unknown[]) => getAccountMe(...a) }))
const googleLinkStart = vi.fn()
vi.mock('../../lib/api', async (importOriginal) => ({
  ...await importOriginal<typeof import('../../lib/api')>(),
  googleLinkStart: (...a: unknown[]) => googleLinkStart(...a),
  googleLoginResult: vi.fn().mockResolvedValue({ status: 'ok' }),
}))

import { AccountSection } from './AccountSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('AccountSection', () => {
  beforeEach(() => getAccountMe.mockReset())

  it('viser email og rolle fra profilen', async () => {
    getAccountMe.mockResolvedValue({
      user_id: 'u1', email: 'bjorn@x.dk', email_verified: true,
      language: 'da', role: 'owner', tier: 'owner',
    })
    render(<AccountSection config={cfg} />)
    await waitFor(() => expect(screen.getByText('bjorn@x.dk')).toBeTruthy())
    // "owner" optræder både som rolle og tier → flere matches er ok.
    expect(screen.getAllByText(/owner/i).length).toBeGreaterThanOrEqual(1)
  })

  it('viser "ikke verificeret" når email_verified=false', async () => {
    getAccountMe.mockResolvedValue({
      user_id: 'u2', email: 'm@x.dk', email_verified: false,
      language: 'en', role: 'member', tier: 'plus',
    })
    render(<AccountSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/ikke verificeret/i)).toBeTruthy())
  })

  it('opens Google account linking in a browser tab reserved during the click', async () => {
    getAccountMe.mockResolvedValue({ user_id: 'u1', email: 'b@x.dk', email_verified: true, role: 'owner', tier: 'owner', google_linked: false })
    googleLinkStart.mockResolvedValue({ authorize_url: 'https://accounts.example/link', nonce: 'n' })
    vi.stubGlobal('jarvisDesk', undefined)
    const popup = { opener: window, location: { href: '' }, close: vi.fn() }
    const open = vi.fn(() => popup)
    vi.stubGlobal('open', open)
    render(<AccountSection config={cfg} />)
    fireEvent.click(await screen.findByRole('button', { name: /Forbind Google-konto/i }))
    expect(open).toHaveBeenCalledWith('about:blank', '_blank')
    await waitFor(() => expect(popup.location.href).toBe('https://accounts.example/link'))
    vi.unstubAllGlobals()
  })
})
