import * as SecureStore from 'expo-secure-store'
import { loadLastSession, saveLastSession } from './sessionStore'

jest.mock('expo-secure-store', () => {
  let v: string | null = null
  return {
    setItemAsync: jest.fn(async (_k: string, val: string) => { v = val }),
    getItemAsync: jest.fn(async () => v),
    deleteItemAsync: jest.fn(async () => { v = null }),
    __saet: (x: string | null) => { v = x },
  }
})
const store = SecureStore as unknown as { __saet: (x: string | null) => void }

beforeEach(() => store.__saet(null))

it('session og flade gemmes SAMMEN', async () => {
  // To noegler kan blive uenige - én kan ikke.
  await saveLastSession('s1', true)
  expect(await loadLastSession()).toEqual({ id: 's1', kode: true })
})

it('chat-fladen huskes ogsaa, ikke kun code', async () => {
  await saveLastSession('s1', false)
  expect(await loadLastSession()).toEqual({ id: 's1', kode: false })
})

it('en GAMMEL bar id-streng laeses stadig', async () => {
  // Noeglen indeholdt foer kun id'et. Uden det her ville alle der opdaterer
  // miste deres sidste samtale én gang - og det ville ligne at appen havde
  // glemt dem.
  store.__saet('chat-gammel')
  expect(await loadLastSession()).toEqual({ id: 'chat-gammel', kode: false })
})

it('tom eller vroevlet vaerdi giver null, ikke en halv plads', async () => {
  store.__saet('')
  expect(await loadLastSession()).toBeNull()
  store.__saet('{ikke json')
  expect(await loadLastSession()).toBeNull()
  store.__saet('{"kode":true}')
  expect(await loadLastSession()).toBeNull()
})

it('et tomt session-id gemmes ikke', async () => {
  await saveLastSession('', true)
  expect(await loadLastSession()).toBeNull()
})
