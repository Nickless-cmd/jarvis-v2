import { render } from '@testing-library/react-native'
import { OfflineNotice } from './OfflineNotice'

describe('OfflineNotice', () => {
  it('renders nothing when connected and no queued work exists', async () => {
    const screen = await render(<OfflineNotice connectivity="connected" reconnecting={false} outboxCount={0} />)
    expect(screen.toJSON()).toBeNull()
  })

  it('explains offline state and queued messages', async () => {
    const screen = await render(<OfflineNotice connectivity="offline" reconnecting={false} outboxCount={2} />)
    expect(screen.getByText('Offline')).toBeTruthy()
    expect(screen.getByText('2 beskeder venter og sendes automatisk.')).toBeTruthy()
  })

  it('explains API reconnecting state', async () => {
    const screen = await render(<OfflineNotice connectivity="reconnecting" reconnecting={false} outboxCount={0} />)
    expect(screen.getByText('Genopretter forbindelse')).toBeTruthy()
  })

  it('explains stream reconnecting while the API is otherwise connected', async () => {
    const screen = await render(<OfflineNotice connectivity="connected" reconnecting outboxCount={0} />)
    expect(screen.getByText('Genforbinder stream')).toBeTruthy()
  })
})
