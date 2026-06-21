import { render, fireEvent, waitFor } from '@testing-library/react-native'
import { TeamsPanel } from './TeamsPanel'
import * as teamsApi from '../lib/teamsApi'

jest.mock('../lib/teamsApi')

describe('TeamsPanel', () => {
  beforeEach(() => {
    ;(teamsApi.listTeams as jest.Mock).mockResolvedValue([])
    ;(teamsApi.listMyInvites as jest.Mock).mockResolvedValue([])
  })
  it('viser "log ind" når config er null (ingen tavs no-op)', async () => {
    const screen = await render(<TeamsPanel config={null} onSelectSession={jest.fn()} />)
    expect(screen.getByText('Log ind for at bruge teams')).toBeTruthy()
    // Ingen input-felter når man ikke er logget ind:
    expect(screen.queryByPlaceholderText('Nyt team-navn')).toBeNull()
  })

  it('viser input-felter når config findes', async () => {
    const screen = await render(
      <TeamsPanel config={{ apiBaseUrl: 'http://x', authToken: 't' }} onSelectSession={jest.fn()} />,
    )
    expect(screen.getByPlaceholderText('Nyt team-navn')).toBeTruthy()
  })

  it('viser pending invite + acceptér via knap (pull-baseret levering)', async () => {
    ;(teamsApi.listMyInvites as jest.Mock).mockResolvedValue([
      { token: 'tok1', team_id: 't1', team_name: 'Familie', invited_by: 'bjorn',
        created_at: '', expires_at: '' },
    ])
    ;(teamsApi.acceptInvite as jest.Mock).mockResolvedValue({ team_id: 't1' })
    const cfg = { apiBaseUrl: 'http://x', authToken: 't' }
    const screen = await render(<TeamsPanel config={cfg} onSelectSession={jest.fn()} />)
    await waitFor(() => expect(screen.getByText(/Du er inviteret til Familie/)).toBeTruthy())
    fireEvent.press(screen.getByText('Acceptér'))
    await waitFor(() => expect(teamsApi.acceptInvite as jest.Mock).toHaveBeenCalledWith(cfg, 'tok1'))
  })
})
