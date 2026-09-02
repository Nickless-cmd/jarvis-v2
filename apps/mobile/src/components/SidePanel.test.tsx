import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { SidePanel } from './SidePanel'

const metrics = {
  frame: { x: 0, y: 0, width: 360, height: 800 },
  insets: { top: 24, left: 0, right: 0, bottom: 0 }
}

function wrap(ui: React.ReactElement) {
  return render(<SafeAreaProvider initialMetrics={metrics}>{ui}</SafeAreaProvider>)
}

const sessions = [
  { id: 's1', title: 'Første samtale', updated_at: '2026-06-18T10:00:00', message_count: 3 },
  { id: 's2', title: 'Anden samtale', updated_at: '2026-06-17T10:00:00', message_count: 1 }
]

const base = {
  onClose: () => undefined,
  displayName: 'Bjørn',
  sessions,
  activeId: 's1' as string | null,
  onSelectSession: () => undefined,
  onNewSession: () => undefined,
  onOpenSettings: () => undefined
}

it('renders nothing when closed', async () => {
  const screen = await wrap(<SidePanel open={false} {...base} />)
  expect(screen.queryByText('Første samtale')).toBeNull()
})

it('lists sessions and selects one', async () => {
  const onSelect = jest.fn()
  const screen = await wrap(<SidePanel open {...base} onSelectSession={onSelect} />)
  await waitFor(() => expect(screen.getByText('Anden samtale')).toBeTruthy())
  fireEvent.press(screen.getByText('Anden samtale'))
  expect(onSelect).toHaveBeenCalledWith('s2')
})

it('filters sessions by search', async () => {
  const screen = await wrap(<SidePanel open {...base} />)
  await waitFor(() => expect(screen.getByText('Første samtale')).toBeTruthy())
  fireEvent.changeText(screen.getByPlaceholderText('Søg samtaler'), 'anden')
  await waitFor(() => expect(screen.queryByText('Første samtale')).toBeNull())
  expect(screen.getByText('Anden samtale')).toBeTruthy()
})

it('opens settings via gear', async () => {
  const onOpenSettings = jest.fn()
  const screen = await wrap(<SidePanel open {...base} onOpenSettings={onOpenSettings} />)
  fireEvent.press(screen.getByLabelText('Indstillinger'))
  expect(onOpenSettings).toHaveBeenCalled()
})
