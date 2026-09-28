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
