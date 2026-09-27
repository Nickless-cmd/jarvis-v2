import { render, waitFor } from '@testing-library/react-native'
import { AuthImage } from './AuthImage'
import type { ApiConfig } from '../lib/types'

/**
 * Hentningen styres pr. test: «venter for evigt» giver pladsen, «svarer» giver
 * billedet. Uden den styring ville begge veje se ens ud, og testen kunne ikke
 * skelne «pladsen står der» fra «billedet kom».
 *
 * Mocken hentes frem med `jest.requireMock` i stedet for at fabrikken lukker
 * over en variabel: `jest.mock` hejses op OVER modulets imports, så en
 * `const`-reference i fabrikken ville ramme TDZ (dødt tidligt) og vælte filen.
 */
jest.mock('expo-file-system/legacy', () => ({
  __esModule: true,
  documentDirectory: 'file:///doc/',
  cacheDirectory: 'file:///cache/',
  getInfoAsync: jest.fn(async () => ({ exists: false, size: 0 })),
  createDownloadResumable: jest.fn(),
}))

const fsMock = jest.requireMock('expo-file-system/legacy') as {
  createDownloadResumable: jest.Mock
}

const config = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } as unknown as ApiConfig

const vis = () => (
  <AuthImage
    config={config}
    url="https://api.srvlab.dk/attachments/image/x"
    navn="x"
    style={{ width: 240, height: 240 }}
    testID="billede"
  />
)

beforeEach(() => {
  fsMock.createDownloadResumable.mockReset()
})

/**
 * Målt 27/9-2026: pladsen var et TOMT felt (`<Image source={{ uri: '' }}>`).
 * Det sagde hverken «der kommer noget» eller «noget gik i stykker» — og på et
 * genereret billede, hvor ventetiden er 20-60 s, stod hullet længe nok til at
 * man troede det var en fejl. Bjørn pegede på ChatGPT-appen som facit: dér
 * ANIMERER pladsen mens billedet laves.
 */
it('viser en plads mens billedet hentes', async () => {
  fsMock.createDownloadResumable.mockReturnValue({
    downloadAsync: () => new Promise(() => {}),
  })
  const s = await render(vis())
  expect(s.getByLabelText('Henter billede')).toBeTruthy()
})

it('pladsen forsvinder når billedet er hentet', async () => {
  fsMock.createDownloadResumable.mockReturnValue({
    downloadAsync: jest.fn(async () => ({ uri: 'file:///cache/img-x' })),
  })
  const s = await render(vis())
  await waitFor(() => expect(s.queryByLabelText('Henter billede')).toBeNull())
  expect(s.getByTestId('billede')).toBeTruthy()
})
