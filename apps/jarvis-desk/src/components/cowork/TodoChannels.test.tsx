import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TodoPane } from './TodoPane'
import { ChannelsPane } from './ChannelsPane'

describe('TodoPane', () => {
  it('viser todos med status', () => {
    render(<TodoPane todos={[{ id: '1', content: 'Byg cowork', status: 'in_progress' }]} />)
    expect(screen.getByText('Byg cowork')).toBeInTheDocument()
  })
})
describe('ChannelsPane', () => {
  it('viser kanaler med online-status', () => {
    render(<ChannelsPane channels={[{ name: 'discord', online: true, unread: 2 }]} />)
    expect(screen.getByText('discord')).toBeInTheDocument()
    expect(screen.getByText(/2/)).toBeInTheDocument()
  })
})
