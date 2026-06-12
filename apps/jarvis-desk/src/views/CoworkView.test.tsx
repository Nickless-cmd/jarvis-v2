import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'

vi.mock('../lib/coworkApi', () => ({
  getCoworkQueue: vi.fn().mockResolvedValue([]),
  getCoworkPlans: vi.fn().mockResolvedValue([]),
  getCoworkTodos: vi.fn().mockResolvedValue([]),
  getCoworkChannels: vi.fn().mockResolvedValue([{ name: 'discord', online: true, unread: 0 }]),
  resolveQueueItem: vi.fn(),
}))
vi.mock('../hooks/useSettings', () => ({ useSettings: () => ({ settings: { apiBaseUrl: 'http://t', authToken: 't' } }) }))

import { CoworkView } from './CoworkView'

describe('CoworkView', () => {
  it('owner: viser kanal-ruden', async () => {
    render(<CoworkView role="owner" />)
    expect(await screen.findByText('Kanaler')).toBeInTheDocument()
  })
  it('member: ingen kanal-rude', () => {
    render(<CoworkView role="member" />)
    expect(screen.queryByText('Kanaler')).toBeNull()
  })
})
