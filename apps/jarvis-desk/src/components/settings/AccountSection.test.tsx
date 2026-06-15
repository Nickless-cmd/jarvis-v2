import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getAccountMe = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAccountMe: (...a: unknown[]) => getAccountMe(...a) }))

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
})
