import { readFileSync } from 'fs'
import { join } from 'path'
import { act, fireEvent, render } from '@testing-library/react-native'
import { FullscreenImagePreview } from './FullscreenImagePreview'

jest.mock('../state/AuthContext', () => ({
  useAuth: () => ({ config: { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'token' } })
}))

jest.mock('expo-media-library/legacy', () => ({
  requestPermissionsAsync: jest.fn(async () => ({ granted: true })),
  saveToLibraryAsync: jest.fn(async () => undefined),
}))

const galleri = () => require('expo-media-library/legacy') as {
  requestPermissionsAsync: jest.Mock
  saveToLibraryAsync: jest.Mock
}
const filsystem = () => require('expo-file-system/legacy') as {
  createDownloadResumable: jest.Mock
}

const vis = (over: Record<string, unknown> = {}) =>
  render(
    <FullscreenImagePreview
      visible
      uri="https://api.srvlab.dk/attachments/image/1e48fd12"
      title="lanterne.png"
      filnavn="lanterne.png"
      mime="image/png"
      onClose={() => undefined}
      {...over}
    />
  )

beforeEach(() => {
  jest.clearAllMocks()
  galleri().requestPermissionsAsync.mockResolvedValue({ granted: true })
  galleri().saveToLibraryAsync.mockResolvedValue(undefined)
  // Deterministisk pr. test. `AuthImage` henter SELV billedet naar den
  // monteres, saa en `mockReturnValueOnce` ville blive spist af DEN hentning
  // foer knappen overhovedet blev trykket.
  //
  // `downloadAsync` returnerer den sti den blev BEDT om — ikke en fast streng.
  // Den rigtige API gør det samme, og uden det kunne testen nedenfor ikke se
  // om filnavnet faktisk bar sin endelse hele vejen til galleriet.
  filsystem().createDownloadResumable.mockImplementation((_url: string, dest: string) => ({
    downloadAsync: jest.fn(async () => ({ uri: dest })),
  }))
})

it('gemmer billedet i galleriet og siger det', async () => {
  const screen = await vis()
  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-download'))
  })

  expect(galleri().saveToLibraryAsync).toHaveBeenCalledTimes(1)
  expect(screen.getByText('Gemt i galleriet')).toBeTruthy()
})

it('filen der gemmes baerer en ENDELSE — uden den afviser galleriet den', async () => {
  // AuthImage navngiver sin cache-kopi efter attachment-id'et, som ikke har
  // nogen endelse. Gemte vi DEN fil, ville galleriet afvise den. Navnet skal
  // derfor bygges med endelsen fra filnavnet eller mime-typen.
  const screen = await vis({ filnavn: '1e48fd12', mime: 'image/jpeg' })
  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-download'))
  })

  const dests = filsystem().createDownloadResumable.mock.calls.map((c) => String(c[1]))
  const dest = dests.find((d) => d.endsWith('.jpg'))
  expect(dest).toBeDefined()
  expect(galleri().saveToLibraryAsync.mock.calls.at(-1)?.[0]).toBe(dest)
})

it('siger det RENT naar brugeren har afvist galleriet', async () => {
  galleri().requestPermissionsAsync.mockResolvedValue({ granted: false })
  galleri().saveToLibraryAsync.mockRejectedValue(new Error('afvist'))
  const screen = await vis()
  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-download'))
  })
  expect(screen.getByText('Galleriet blev ikke tilladt — billedet er ikke gemt')).toBeTruthy()
})

it('melder fejl naar hentningen ikke gav en fil', async () => {
  filsystem().createDownloadResumable.mockImplementation(() => ({
    downloadAsync: jest.fn(async () => ({ uri: null })),
  }))
  const screen = await vis()
  await act(async () => {
    fireEvent.press(screen.getByTestId('attachment-download'))
  })
  expect(screen.getByText('Kunne ikke gemme billedet')).toBeTruthy()
  expect(galleri().saveToLibraryAsync).not.toHaveBeenCalled()
})

it('viser billedet gennem AuthImage — ikke en <Image> der taber sin header', async () => {
  const screen = await vis()
  expect(screen.getByTestId('attachment-fullscreen-image')).toBeTruthy()
})

/**
 * Kilde-vagt. Gribbetaget er usynligt i en test — det kraever en finger — saa
 * en fremtidig omskrivning kunne fjerne knibningen uden at én test blev rød.
 * Vagten fanger netop det.
 */
it('knib og panorering er koblet PAA scenen, ikke bare skrevet', () => {
  const kilde = readFileSync(join(__dirname, 'FullscreenImagePreview.tsx'), 'utf8')
  expect(kilde).toMatch(/PanResponder\.create/)
  expect(kilde).toMatch(/\{\.\.\.pan\.panHandlers\}/)
  // Gribbetaget maa ikke tage trykket fra knapperne.
  expect(kilde).toMatch(/onStartShouldSetPanResponder: \(\) => false/)
})
