import { readFileSync } from 'fs'
import { join } from 'path'
import { fireEvent, render, waitFor } from '@testing-library/react-native'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { SidePanel } from './SidePanel'
import { I18nProvider } from '../i18n/I18nContext'

const metrics = {
  frame: { x: 0, y: 0, width: 360, height: 800 },
  insets: { top: 24, left: 0, right: 0, bottom: 0 }
}

function wrap(ui: React.ReactElement) {
  return render(<SafeAreaProvider initialMetrics={metrics}>{ui}</SafeAreaProvider>)
}

function wrapEn(ui: React.ReactElement) {
  return render(
    <I18nProvider initialLocale="en">
      <SafeAreaProvider initialMetrics={metrics}>{ui}</SafeAreaProvider>
    </I18nProvider>,
  )
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

it('bruger appens valgte sprog til panel chrome', async () => {
  const screen = await wrapEn(
    <SidePanel
      open
      {...base}
      bubbleSupported
      activeId="s1"
      onFloatActive={jest.fn()}
      onOpenArtifacts={jest.fn()}
      onOpenActivity={jest.fn()}
      onOpenChatSettings={jest.fn()}
      onSkiftFlade={jest.fn()}
    />,
  )
  fireEvent.press(screen.getByTestId('panel-search-toggle'))
  expect(await screen.findByPlaceholderText('Search conversations')).toBeTruthy()
  expect(screen.getByText('Move chat to bubble')).toBeTruthy()
  expect(screen.getByText('Activity')).toBeTruthy()
  expect(screen.getByText('This conversation')).toBeTruthy()
  expect(screen.getByText('Settings')).toBeTruthy()
  expect(screen.getByText('New chat')).toBeTruthy()
  expect(screen.queryByPlaceholderText('Søg samtaler')).toBeNull()
  expect(screen.queryByText('Flyt chat til boble')).toBeNull()
  expect(screen.queryByText('Aktivitet')).toBeNull()
  expect(screen.queryByText('Denne samtale')).toBeNull()
  expect(screen.queryByText('Indstillinger')).toBeNull()
  expect(screen.queryByText('Ny samtale')).toBeNull()
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

// --- flade-feltet (chat <-> code) ---

it('uden onSkiftFlade tegnes feltet slet ikke', async () => {
  // Et felt der ikke kan skifte noget er en knap der lyver.
  const screen = await wrap(<SidePanel open {...base} />)
  expect(screen.queryByTestId('skift-flade')).toBeNull()
})

it('i CHAT hedder feltet Code og foerer IND', async () => {
  const onSkift = jest.fn()
  const screen = await wrap(<SidePanel open {...base} onSkiftFlade={onSkift} />)
  fireEvent.press(screen.getByText('Code'))
  expect(onSkift).toHaveBeenCalledWith(true)
})

it('i CODE hedder SAMME felt Tilbage til chat og foerer UD', async () => {
  // Bjoern bad om et «tilbage til chat felt naar man er i code mode». Doeren
  // skal aabne begge veje - ellers har code-fladen ingen indgang.
  const onSkift = jest.fn()
  const screen = await wrap(<SidePanel open {...base} kodeTilstand onSkiftFlade={onSkift} />)
  fireEvent.press(screen.getByText('Tilbage til chat'))
  expect(onSkift).toHaveBeenCalledWith(false)
})

it('feltet siger ikke Code naar man allerede ER i code', async () => {
  const screen = await wrap(<SidePanel open {...base} kodeTilstand onSkiftFlade={jest.fn()} />)
  expect(screen.queryByText('Code')).toBeNull()
})

// ── navnets mærke (21/9-2026) ─────────────────────────────────────────────
//
// Foer stod der en accent-farvet cirkel med en prik i midten — «det gamle ring
// ikon» (Bjørn). Den form hoerer til foer Puls-maerket. Desk har maerket her, og
// nu ogsaa telefonen: samme tegn paa begge enheder.

it('navnet baerer Puls-maerket, ikke den gamle ring', async () => {
  const screen = await wrap(<SidePanel open {...base} />)
  expect(screen.getByTestId('puls-ikon')).toBeTruthy()
})

it('den gamle rings form findes ikke laengere i panelet', () => {
  // Kontrolarm: en render-test kan ikke se FRAVAERET af et View uden testID,
  // saa den gamle form laases i kilden — som kodeFlade.kobling.test.ts goer.
  // Uden den kunne nogen saette cirklen tilbage uden at en test sagde fra.
  const kilde = readFileSync(join(__dirname, 'SidePanel.tsx'), 'utf8')
  expect(kilde).not.toContain('ringInner')
  expect(kilde).not.toMatch(/styles\.ring\b/)
})

// ── session-raekken: tag, fade og puls (21/9-2026) ────────────────────────
//
// Bjoern: «chat og kode sessioner mangler samme start tag som i desk ... og
// enden af sessions navnet skal have fade som i desk og istedet for den
// groenne prik over de 3 prikker som er menu ... dit eget animeret ikon».
//
// Raekken er nu desk's: [tag] [titel med fade] [puls] [menu].

const fladeSessions = [
  { id: 'c1', title: 'En chat', updated_at: '2026-06-18T10:00:00', message_count: 2, kind: 'chat' as const },
  { id: 'k1', title: 'En kode-samtale', updated_at: '2026-06-17T10:00:00', message_count: 4, kind: 'code' as const },
]

it('hver session baerer sin flades tag — besked for chat, <> for kode', async () => {
  const screen = await wrap(<SidePanel open {...base} sessions={fladeSessions} activeId={null} />)
  // Tagget er FAST: uden det laa en code-session i samme liste som en chat
  // uden at nogen kunne se hvilken der var hvilken.
  expect(screen.getByTestId('session-tag-chat')).toBeTruthy()
  expect(screen.getByTestId('session-tag-code')).toBeTruthy()
})

it('titel-enden fader ud i fladen', async () => {
  const screen = await wrap(<SidePanel open {...base} />)
  // Én fade pr. raekke — `base` har to sessioner, altsaa to kanter.
  expect(screen.getAllByTestId('session-fade')).toHaveLength(sessions.length)
})

it('en arbejdende session baerer den ANIMEREDE puls', async () => {
  const screen = await wrap(<SidePanel open {...base} workingIds={['s2']} />)
  expect(screen.getByTestId('session-puls-arbejder')).toBeTruthy()
  expect(screen.queryByTestId('session-puls-ulaest')).toBeNull()
})

it('en ulaest session baerer maerket i ro — ikke prikken', async () => {
  const screen = await wrap(<SidePanel open {...base} unreadIds={{ s2: true }} />)
  expect(screen.getByTestId('session-puls-ulaest')).toBeTruthy()
  expect(screen.queryByTestId('session-puls-arbejder')).toBeNull()
})

it('ingen aktivitet giver ingen puls', async () => {
  const screen = await wrap(<SidePanel open {...base} />)
  expect(screen.queryByTestId('session-puls-arbejder')).toBeNull()
  expect(screen.queryByTestId('session-puls-ulaest')).toBeNull()
})

it('prikken findes ikke laengere i raekken', () => {
  // Kontrolarm: «den groenne prik» (unreadDot) og hjerte-prikken
  // (HeartbeatDot) skal vaere VAEK. Stod begge, ville to tegn betyde det
  // samme — og prikken laa oven paa de tre prikker, som Bjoern bad om at
  // slippe for.
  const kilde = readFileSync(join(__dirname, 'SidePanel.tsx'), 'utf8')
  expect(kilde).not.toContain('unreadDot')
  expect(kilde).not.toContain('HeartbeatDot')
  expect(kilde).toContain('AnimeretPuls')
})
