import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { vi, describe, it, expect, beforeEach } from 'vitest'
import { TeamsSection } from './TeamsSection'

vi.mock('../../hooks/useSettings', () => ({
  useSettings: () => ({ settings: { apiBaseUrl: 'http://x', authToken: 't' }, auth: { role: 'owner' } }),
}))

const createTeam = vi.fn()
const inviteToTeam = vi.fn()
const listTeams = vi.fn()
vi.mock('../../lib/teamsApi', () => ({
  listTeams: (...a: unknown[]) => listTeams(...a),
  createTeam: (...a: unknown[]) => createTeam(...a),
  inviteToTeam: (...a: unknown[]) => inviteToTeam(...a),
  listTeamSessions: vi.fn(async () => []),
  createTeamSession: vi.fn(async () => ({ session_id: 's1', title: 'x' })),
}))

describe('TeamsSection', () => {
  beforeEach(() => {
    createTeam.mockReset().mockResolvedValue({ team_id: 't1', name: 'Familie', members: [] })
    inviteToTeam.mockReset()
    listTeams.mockReset().mockResolvedValue([])
  })

  it('opretter team via inline-felt (ikke window.prompt)', async () => {
    const promptSpy = vi.spyOn(window, 'prompt')
    render(<TeamsSection onOpenSession={vi.fn()} />)
    await userEvent.click(screen.getByTitle('Nyt team'))
    await userEvent.type(screen.getByLabelText('Nyt team-navn'), 'Familie')
    await userEvent.click(screen.getByText('Opret'))
    await waitFor(() => expect(createTeam).toHaveBeenCalledWith(
      { apiBaseUrl: 'http://x', authToken: 't' }, 'Familie',
    ))
    expect(promptSpy).not.toHaveBeenCalled()
  })

  it('viser fejl-status når invite fejler (ingen tavs no-op)', async () => {
    listTeams.mockResolvedValue([{ team_id: 't1', name: 'Familie', members: [{ user_id: 'bjorn', team_role: 'owner' }] }])
    inviteToTeam.mockRejectedValue(new Error('403'))
    render(<TeamsSection onOpenSession={vi.fn()} />)
    await userEvent.click(await screen.findByText(/Familie/))
    await userEvent.type(screen.getByLabelText('Inviter'), 'mikkel')
    await userEvent.click(screen.getByText('+ Inviter'))
    expect(await screen.findByText(/Kunne ikke invitere/)).toBeInTheDocument()
  })
})
