import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getAccountQuota = vi.fn()
vi.mock('../../lib/coworkApi', () => ({ getAccountQuota: (...a: unknown[]) => getAccountQuota(...a) }))

import { KvoteSection } from './KvoteSection'

const cfg = { apiBaseUrl: 'http://x', authToken: 't' }

describe('KvoteSection', () => {
  beforeEach(() => getAccountQuota.mockReset())

  it('viser tier og forbrug pr. type', async () => {
    getAccountQuota.mockResolvedValue({
      tier: 'plus',
      items: [
        { kind: 'chat', used: 5, limit: null, remaining: null, warn: false },
        { kind: 'cowork', used: 9, limit: 10, remaining: 1, warn: true },
      ],
    })
    render(<KvoteSection config={cfg} />)
    await waitFor(() => expect(screen.getByText(/plus/i)).toBeTruthy())
    expect(screen.getByText(/ubegrænset/i)).toBeTruthy()   // chat
    expect(screen.getByText('9 / 10')).toBeTruthy()        // cowork
  })

  it('markerer warn-rækker', async () => {
    getAccountQuota.mockResolvedValue({
      tier: 'free',
      items: [{ kind: 'cowork', used: 0, limit: 0, remaining: 0, warn: true }],
    })
    const { container } = render(<KvoteSection config={cfg} />)
    await waitFor(() => expect(container.querySelector('.quota-row.warn')).toBeTruthy())
  })
})
