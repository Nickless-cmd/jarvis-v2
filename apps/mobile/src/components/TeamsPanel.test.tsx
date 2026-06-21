import { render } from '@testing-library/react-native'
import { TeamsPanel } from './TeamsPanel'
import * as teamsApi from '../lib/teamsApi'

jest.mock('../lib/teamsApi')

describe('TeamsPanel', () => {
  it('viser "log ind" når config er null (ingen tavs no-op)', async () => {
    const screen = await render(<TeamsPanel config={null} onSelectSession={jest.fn()} />)
    expect(screen.getByText('Log ind for at bruge teams')).toBeTruthy()
    // Ingen input-felter når man ikke er logget ind:
    expect(screen.queryByPlaceholderText('Nyt team-navn')).toBeNull()
  })

  it('viser input-felter når config findes', async () => {
    ;(teamsApi.listTeams as jest.Mock).mockResolvedValue([])
    const screen = await render(
      <TeamsPanel config={{ apiBaseUrl: 'http://x', authToken: 't' }} onSelectSession={jest.fn()} />,
    )
    expect(screen.getByPlaceholderText('Nyt team-navn')).toBeTruthy()
  })
})
