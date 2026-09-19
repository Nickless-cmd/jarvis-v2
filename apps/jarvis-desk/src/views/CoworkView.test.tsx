import { beforeEach, describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { act } from 'react'
import { emitZone } from '../lib/coworkZone'

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
  beforeEach(() => emitZone('mc'))
  it('owner: Mission Control viser kontrolcenter med faner (inkl. Agenter)', () => {
    render(<CoworkView role="owner" />)
    expect(screen.getByText('Oversigt')).toBeTruthy()
    expect(screen.getAllByText('Agenter').length).toBeGreaterThan(0)  // owner-only fane+rude
  })

  it('member: ingen Agenter (owner-only)', () => {
    render(<CoworkView role="member" />)
    expect(screen.getByText('Oversigt')).toBeTruthy()
    expect(screen.queryAllByText('Agenter').length).toBe(0)
  })

  it('skift til Indstillinger-zone (via emitZone) viser Account-profilen', async () => {
    render(<CoworkView role="owner" />)
    // Zone-skift kommer nu fra Sidebar via emitZone — ikke en intern rail-knap.
    act(() => emitZone('settings'))
    await waitFor(() => expect(screen.getByText('bjorn@x.dk')).toBeTruthy())
  })

  it('samler de små personlige indstillinger på Generelt', async () => {
    render(<CoworkView role="owner" />)
    act(() => emitZone('location'))
    expect(screen.getByRole('heading', { name: 'Generelt', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Udseende', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Lokation', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Notifikationer', level: 2 })).toBeInTheDocument()
    await act(async () => {})
  })

  it('samler konto, enheder og privatliv på Konto og sikkerhed', async () => {
    render(<CoworkView role="owner" />)
    act(() => emitZone('privacy'))
    expect(screen.getByRole('heading', { name: 'Konto og sikkerhed', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Privatliv og tilladelser' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Profil og enheder' })).toBeInTheDocument()
    await act(async () => {})
  })

  it('samler marketplace og forbindelser på én side', async () => {
    render(<CoworkView role="owner" />)
    act(() => emitZone('marketplace'))
    expect(screen.getByRole('heading', { name: 'Værktøjer og forbindelser', level: 1 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Marketplace', level: 2 })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'Apps, MCP og plugins', level: 2 })).toBeInTheDocument()
    await act(async () => {})
  })
})
