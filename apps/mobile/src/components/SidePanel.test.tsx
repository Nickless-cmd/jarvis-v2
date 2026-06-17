import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { SidePanel } from './SidePanel'

const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' }

jest.mock('../lib/apiClient', () => ({
  listConnectors: jest.fn().mockResolvedValue([
    { id: 'github', name: 'GitHub', kind: 'oauth', category: 'Dev', icon: 'g', desc: '', status: 'available', connected: true, enabled: true }
  ]),
  setConnectorEnabled: jest.fn().mockResolvedValue(undefined)
}))

const metrics = {
  frame: { x: 0, y: 0, width: 360, height: 800 },
  insets: { top: 24, left: 0, right: 0, bottom: 0 }
}

function wrap(ui: React.ReactElement) {
  return render(<SafeAreaProvider initialMetrics={metrics}>{ui}</SafeAreaProvider>)
}

const sessions = [
  { id: 's1', title: 'Første samtale', updated_at: '', message_count: 3 },
  { id: 's2', title: 'Anden samtale', updated_at: '', message_count: 1 }
]

it('renders nothing when closed', async () => {
  const screen = await wrap(
    <SidePanel
      open={false}
      onClose={() => undefined}
      config={config}
      displayName="Bjørn"
      sessions={sessions}
      activeId="s1"
      onSelectSession={() => undefined}
      onNewSession={() => undefined}
      onSignOut={() => undefined}
    />
  )
  expect(screen.queryByText('Sessioner')).toBeNull()
})

it('lists sessions and selects one when open', async () => {
  const onSelect = jest.fn()
  const screen = await wrap(
    <SidePanel
      open
      onClose={() => undefined}
      config={config}
      displayName="Bjørn"
      sessions={sessions}
      activeId="s1"
      onSelectSession={onSelect}
      onNewSession={() => undefined}
      onSignOut={() => undefined}
    />
  )

  await waitFor(() => expect(screen.getByText('Anden samtale')).toBeTruthy())
  fireEvent.press(screen.getByText('Anden samtale'))
  expect(onSelect).toHaveBeenCalledWith('s2')
})

it('shows connectors fetched for the user', async () => {
  const screen = await wrap(
    <SidePanel
      open
      onClose={() => undefined}
      config={config}
      displayName="Bjørn"
      sessions={sessions}
      activeId={null}
      onSelectSession={() => undefined}
      onNewSession={() => undefined}
      onSignOut={() => undefined}
    />
  )

  await waitFor(() => expect(screen.getByText('GitHub')).toBeTruthy())
})

it('fires sign-out', async () => {
  const onSignOut = jest.fn()
  const screen = await wrap(
    <SidePanel
      open
      onClose={() => undefined}
      config={config}
      displayName="Bjørn"
      sessions={sessions}
      activeId={null}
      onSelectSession={() => undefined}
      onNewSession={() => undefined}
      onSignOut={onSignOut}
    />
  )
  fireEvent.press(screen.getByText('Log ud'))
  expect(onSignOut).toHaveBeenCalled()
})
