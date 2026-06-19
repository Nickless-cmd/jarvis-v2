import * as SecureStore from 'expo-secure-store'
import { loadLastSeen, markSeen } from './lastSeen'

jest.mock('expo-secure-store', () => {
  let store: Record<string, string> = {}
  return {
    getItemAsync: jest.fn(async (k: string) => store[k] ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => { store[k] = v }),
    __reset: () => { store = {} },
  }
})

beforeEach(() => { (SecureStore as unknown as { __reset: () => void }).__reset() })

describe('lastSeen', () => {
  it('markSeen + loadLastSeen round-trip', async () => {
    await markSeen('s1', 4)
    await markSeen('s2', 7)
    expect(await loadLastSeen()).toEqual({ s1: 4, s2: 7 })
  })
  it('tom når intet gemt', async () => {
    expect(await loadLastSeen()).toEqual({})
  })
  it('korrupt JSON → tom', async () => {
    await SecureStore.setItemAsync('jarvis.mobile.lastSeen', '{ ugyldig')
    expect(await loadLastSeen()).toEqual({})
  })
})
