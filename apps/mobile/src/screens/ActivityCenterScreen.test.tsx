import { render } from '@testing-library/react-native'
import { ActivityCenterScreen } from './ActivityCenterScreen'

it('shows active runs as a mobile activity center', async () => {
  const screen = await render(
    <ActivityCenterScreen
      onClose={jest.fn()}
      runs={[{ sessionId: 's1', runId: 'r1', status: 'working' }]}
      outboxCount={2}
      presenceSummary="Pixel aktiv"
    />
  )

  expect(screen.getByText('Aktivitet')).toBeTruthy()
  expect(screen.getByText('r1')).toBeTruthy()
  expect(screen.getByText('2 i kø')).toBeTruthy()
})
