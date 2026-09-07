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
