import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'

vi.mock('../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' }, auth: { role: 'owner' } }),
}))
vi.mock('../hooks/useCoworkData', () => ({
  useCoworkData: () => ({
    queue: [], plans: [], todos: [], channels: [{ name: 'discord', online: true, unread: 0 }],
    shareGuard: [], agents: [], resolve: vi.fn(), resolveShare: vi.fn(),
  }),
}))
const getAccountMe = vi.fn().mockResolvedValue({
  user_id: 'u1', email: 'bjorn@x.dk', email_verified: true, language: 'da', role: 'owner', tier: 'owner',
})
const getAccountQuota = vi.fn().mockResolvedValue({ tier: 'owner', items: [] })
vi.mock('../lib/coworkApi', async (orig) => ({
  ...(await orig<typeof import('../lib/coworkApi')>()),
  getAccountMe: (...a: unknown[]) => getAccountMe(...a),
  getAccountQuota: (...a: unknown[]) => getAccountQuota(...a),
}))
// TotpSetup/PluginsPanel laver netværkskald ved mount — stub dem til tomme noder.
vi.mock('../components/settings/TotpSetup', () => ({ TotpSetup: () => <div>totp</div> }))
vi.mock('../components/settings/PluginsPanel', () => ({ PluginsPanel: () => <div>plugins</div> }))

import { CoworkView } from './CoworkView'

describe('CoworkView command center', () => {
  it('owner: Mission Control default viser kanal-ruden', () => {
    render(<CoworkView role="owner" />)
    expect(screen.getByText('Kanaler')).toBeTruthy()
  })

  it('member: ingen kanal-rude', () => {
    render(<CoworkView role="member" />)
    expect(screen.queryByText('Kanaler')).toBeNull()
  })

  it('skift til Indstillinger viser Account-profilen', async () => {
    render(<CoworkView role="owner" />)
    fireEvent.click(screen.getByRole('button', { name: /indstillinger/i }))
    await waitFor(() => expect(screen.getByText('bjorn@x.dk')).toBeTruthy())
  })
})
