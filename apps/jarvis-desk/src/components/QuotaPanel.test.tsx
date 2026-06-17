import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

const getQuota = vi.fn()
vi.mock('../lib/accountApi', () => ({ getQuota: (...a: unknown[]) => getQuota(...a) }))

import { QuotaPanel } from './QuotaPanel'

describe('QuotaPanel', () => {
  beforeEach(() => getQuota.mockReset())

  it('viser intet uden config', () => {
    const { container } = render(<QuotaPanel />)
    expect(container.firstChild).toBeNull()
  })

  it('viser tier + forbrug pr. type', async () => {
    getQuota.mockResolvedValue({
      tier: 'plus',
      items: [
        { kind: 'chat', used: 12, limit: 100, remaining: 88, warn: false },
        { kind: 'agent', used: 5, limit: null, remaining: null, warn: false },
      ],
    })
    render(<QuotaPanel config={{ apiBaseUrl: 'http://x', authToken: 't' }} />)
    await waitFor(() => expect(screen.getByText('plus')).toBeInTheDocument())
    expect(screen.getByText('Chat')).toBeInTheDocument()
    expect(screen.getByText('88')).toBeInTheDocument()
    expect(screen.getAllByText('∞').length).toBeGreaterThan(0)  // ubegrænset agent
  })
})
