jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined)
}))
jest.mock('expo-application', () => ({ nativeApplicationVersion: '0.2.18' }))

// jest.mock hejses over alt andet, saa fabrikken maa ikke lukke om lokale
// variabler. Mock'ene laves derfor INDE i fabrikken og hentes bagefter.
jest.mock('./broKlient', () => {
  const start = jest.fn()
  const stop = jest.fn()
  return { opretBro: jest.fn(() => ({ start, stop })), __start: start, __stop: stop }
})
jest.mock('./telefonHandlere', () => ({
  KAN_UDFOERE: ['phone_photo', 'phone_location'],
  udfoerVaerktoej: jest.fn()
}))

import * as SecureStore from 'expo-secure-store'
import { opretBro } from './broKlient'

const { __start: start, __stop: stop } = jest.requireMock('./broKlient') as {
  __start: jest.Mock; __stop: jest.Mock
}
import { startBro, klientId } from './broOpstart'

const CONFIG = { apiBaseUrl: 'https://api.srvlab.dk/', authToken: 'test-token' } // noqa: literal-credential

afterEach(() => jest.clearAllMocks())

describe('klient-id', () => {
  it('genbruges på tværs af opstarter', async () => {
    // Et nyt id hver opstart ville lade registret samle døde forbindelser,
    // fordi broen kun erstatter en klient med SAMME client_id.
    ;(SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce('mobil-abc123')
    expect(await klientId()).toBe('mobil-abc123')
    expect(SecureStore.setItemAsync).not.toHaveBeenCalled()
  })

  it('laves og gemmes første gang', async () => {
    const id = await klientId()
    expect(id).toMatch(/^mobil-/)
    expect(SecureStore.setItemAsync).toHaveBeenCalledWith('jarvis.mobile.broKlientId', id)
  })

  it('virker også hvis SecureStore er utilgængelig', async () => {
    // Uden fallback ville broen slet ikke starte på en telefon hvor
    // nøgleringen af en eller anden grund ikke svarer.
    ;(SecureStore.getItemAsync as jest.Mock).mockRejectedValueOnce(new Error('låst'))
    ;(SecureStore.setItemAsync as jest.Mock).mockRejectedValueOnce(new Error('låst'))
    expect(await klientId()).toMatch(/^mobil-/)
  })
})

describe('startBro', () => {
  it('starter broen og melder handlernes navne som capabilities', async () => {
    startBro(CONFIG)
    await new Promise((r) => setTimeout(r, 0))

    expect(start).toHaveBeenCalled()
    const arg = (opretBro as jest.Mock).mock.calls[0][0]
    expect(arg.capabilities).toEqual(['phone_photo', 'phone_location'])
    expect(arg.apiBaseUrl).toBe('https://api.srvlab.dk/')
    expect(arg.clientId).toMatch(/^mobil-/)
  })

  it('stopperen lukker broen', async () => {
    const stopper = startBro(CONFIG)
    await new Promise((r) => setTimeout(r, 0))
    stopper()
    expect(stop).toHaveBeenCalled()
  })

  it('stopper man FØR id-opslaget er færdigt, startes broen aldrig', async () => {
    // Logger man ud i det sekund appen åbner, må der ikke ligge en bro
    // tilbage der forbinder med et token der ikke gælder længere.
    const stopper = startBro(CONFIG)
    stopper()
    await new Promise((r) => setTimeout(r, 0))
    expect(start).not.toHaveBeenCalled()
  })
})
