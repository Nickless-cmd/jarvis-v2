import { act, fireEvent, render } from '@testing-library/react-native'
import { AttachMenu } from './AttachMenu'
import { byggeKontekster } from '../lib/recentContexts'

jest.mock('expo-media-library/legacy', () => ({
  getPermissionsAsync: jest.fn().mockResolvedValue({ granted: false }),
  requestPermissionsAsync: jest.fn().mockResolvedValue({ granted: false }),
  getAssetsAsync: jest.fn().mockResolvedValue({ assets: [] }),
}))

const base = {
  visible: true,
  onCamera: jest.fn(),
  onGallery: jest.fn(),
  onClose: jest.fn(),
}

const kontekster = byggeKontekster({
  kameraTilladt: true,
  lokationsPraecision: 'off',
  udklipHarTekst: true,
  enhedsNavn: 'Bjørns telefon',
})

it('striben vises ikke når skærmen ikke leverer nogen kontekster', async () => {
  const screen = await render(<AttachMenu {...base} />)
  expect(screen.queryByTestId('attach-contexts')).toBeNull()
})

it('aabner en kompakt menu med separate foto- og filvalg over komponisten', async () => {
  const onGallery = jest.fn()
  const onUpload = jest.fn()
  const screen = await render(<AttachMenu {...base} onGallery={onGallery} onUpload={onUpload} bottomOffset={110} />)
  expect(screen.getByTestId('attach-popover')).toHaveStyle({ bottom: 110 })
  expect(screen.queryByText('Tilføj filer')).toBeNull()
  await act(async () => { fireEvent.press(screen.getByText('Upload foto')) })
  await act(async () => { fireEvent.press(screen.getByText('Upload fil')) })
  expect(onGallery).toHaveBeenCalledTimes(1)
  expect(onUpload).toHaveBeenCalledTimes(1)
})

it('bevarer genvejen til de seneste billeder som undermenu', async () => {
  const screen = await render(<AttachMenu {...base} onPick={jest.fn()} />)
  await act(async () => { fireEvent.press(screen.getByText('Seneste billeder')) })
  expect(screen.getByText('Tilføj filer')).toBeTruthy()
  await act(async () => { fireEvent.press(screen.getByLabelText('Luk')) })
  expect(screen.getByText('Upload foto')).toBeTruthy()
})

it('viser de kontekster skærmen leverer', async () => {
  const screen = await render(<AttachMenu {...base} kontekster={kontekster} onKontekst={jest.fn()} />)
  expect(screen.getByTestId('attach-ctx-udklip')).toBeTruthy()
  expect(screen.getByTestId('attach-ctx-lokation')).toBeTruthy()
})

it('en slukket kontekst kan ikke trykkes — og siger hvorfor', async () => {
  const onKontekst = jest.fn()
  const screen = await render(<AttachMenu {...base} kontekster={kontekster} onKontekst={onKontekst} />)
  await act(async () => { fireEvent.press(screen.getByTestId('attach-ctx-lokation')) })
  expect(onKontekst).not.toHaveBeenCalled()
  expect(screen.getByText('Lokation er slået fra')).toBeTruthy()
})

it('melder hvilken kontekst der blev valgt', async () => {
  const onKontekst = jest.fn()
  const screen = await render(<AttachMenu {...base} kontekster={kontekster} onKontekst={onKontekst} />)
  await act(async () => { fireEvent.press(screen.getByTestId('attach-ctx-udklip')) })
  expect(onKontekst).toHaveBeenCalledWith('udklip')
})

// ── Research (28/9-2026) ───────────────────────────────────────────────────
// Bjørn: «research flyttet til plus menu». Den laa foer som et ikon i
// komponistens kontrol-raekke, hvor den stod sammen med tilladelser og model.
// Den hoerer her: den er noget man SLAAR TIL, ikke noget man trykker paa.
it('research-tilstanden kan slaas til her — den bor ikke i komponisten mere', async () => {
  const onResearchModeChange = jest.fn()
  const screen = await render(
    <AttachMenu {...base} researchMode={false} onResearchModeChange={onResearchModeChange} />
  )
  expect(screen.getByText('Research')).toBeTruthy()
  expect(screen.getByText('Fra')).toBeTruthy()

  await act(async () => { fireEvent.press(screen.getByTestId('attach-research')) })

  expect(onResearchModeChange).toHaveBeenCalledWith(true)
})

it('research-raekken viser TIL og kan slaas fra igen', async () => {
  const onResearchModeChange = jest.fn()
  const screen = await render(
    <AttachMenu {...base} researchMode onResearchModeChange={onResearchModeChange} />
  )
  expect(screen.getByText('Til')).toBeTruthy()

  await act(async () => { fireEvent.press(screen.getByTestId('attach-research')) })

  expect(onResearchModeChange).toHaveBeenCalledWith(false)
})

it('uden onResearchModeChange er der ingen research-raekke', async () => {
  const screen = await render(<AttachMenu {...base} />)
  expect(screen.queryByTestId('attach-research')).toBeNull()
})
