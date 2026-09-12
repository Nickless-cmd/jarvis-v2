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
  // Soegefeltet er foldet sammen som standard — ikonet i toppen folder det ud.
  // Feltet stod foer og fyldte en linje hele tiden for noget man goer sjaeldent.
  fireEvent.press(screen.getByTestId('panel-search-toggle'))
  const felt = await screen.findByPlaceholderText('Søg samtaler')
  fireEvent.changeText(felt, 'anden')
  await waitFor(() => expect(screen.queryByText('Første samtale')).toBeNull())
  expect(screen.getByText('Anden samtale')).toBeTruthy()
})

it('opens settings via gear', async () => {
  const onOpenSettings = jest.fn()
  const screen = await wrap(<SidePanel open {...base} onOpenSettings={onOpenSettings} />)
  fireEvent.press(screen.getByLabelText('Indstillinger'))
  expect(onOpenSettings).toHaveBeenCalled()
})

it('bruger native ikoner i faste controls frem for emoji tekst', async () => {
  const screen = await wrap(<SidePanel open {...base} bubbleSupported onFloatActive={jest.fn()} />)
  fireEvent.press(screen.getByTestId('panel-search-toggle'))
  await waitFor(() => expect(screen.getByPlaceholderText('Søg samtaler')).toBeTruthy())
  expect(screen.queryByText('⚙')).toBeNull()
  expect(screen.queryByText('🔍')).toBeNull()
  expect(screen.queryByText('🫧')).toBeNull()
})

// ── panelets ombygning (12/9-2026) ───────────────────────────────────────
//
// Foer sad fem navnloese ikoner i toppen ved siden af navnet, og soegefeltet
// fyldte en hel linje nedenfor. Det var omvendt af hvor tit de bruges: man
// soeger sjaeldent, og en oejenpaere siger ikke hvad den goer.

it('de fem genveje er FELTER med navn, ikke navnloese ikoner', async () => {
  const screen = await wrap(
    <SidePanel open {...base} bubbleSupported activeId="s1"
      onFloatActive={jest.fn()} onOpenArtifacts={jest.fn()}
      onOpenActivity={jest.fn()} onOpenChatSettings={jest.fn()} />
  )
  // Teksten skal staa paa skaermen — ikke kun som et accessibility-navn.
  expect(screen.getByText('Artifacts')).toBeTruthy()
  expect(screen.getByText('Aktivitet')).toBeTruthy()
  expect(screen.getByText('Denne samtale')).toBeTruthy()
  expect(screen.getByText('Flyt chat til boble')).toBeTruthy()
})

it('soegefeltet er foldet sammen indtil ikonet trykkes', async () => {
  const screen = await wrap(<SidePanel open {...base} />)
  expect(screen.queryByPlaceholderText('Søg samtaler')).toBeNull()
  fireEvent.press(screen.getByTestId('panel-search-toggle'))
  expect(await screen.findByPlaceholderText('Søg samtaler')).toBeTruthy()
})

it('indstillinger staar som et felt med navn', async () => {
  const onOpenSettings = jest.fn()
  const screen = await wrap(<SidePanel open {...base} onOpenSettings={onOpenSettings} />)
  // Kontrolarm mod at den bare forsvandt under ombygningen.
  fireEvent.press(screen.getByTestId('open-settings'))
  expect(onOpenSettings).toHaveBeenCalled()
  expect(screen.getByText('Indstillinger')).toBeTruthy()
})
