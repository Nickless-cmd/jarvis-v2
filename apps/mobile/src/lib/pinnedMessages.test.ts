import * as SecureStore from 'expo-secure-store'
import { laesPins, skiftPin, ryd, pinnedeIRaekkefoelge } from './pinnedMessages'

jest.mock('expo-secure-store', () => {
  const lager: Record<string, string> = {}
  return {
    __lager: lager,
    getItemAsync: jest.fn(async (k: string) => lager[k] ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => { lager[k] = v }),
    deleteItemAsync: jest.fn(async (k: string) => { delete lager[k] }),
  }
})

beforeEach(() => {
  const l = (SecureStore as unknown as { __lager: Record<string, string> }).__lager
  Object.keys(l).forEach((k) => delete l[k])
  jest.clearAllMocks()
})

it('slår fast og løs igen', async () => {
  expect(await skiftPin('s1', 'm1')).toEqual(['m1'])
  expect(await skiftPin('s1', 'm2')).toEqual(['m1', 'm2'])
  expect(await skiftPin('s1', 'm1')).toEqual(['m2'])
})

it('holder sessioner adskilt — en pin må ikke lække til en anden samtale', async () => {
  await skiftPin('s1', 'm1')
  expect(await laesPins('s2')).toEqual([])
})

it('renser session-id til en lovlig nøgle', async () => {
  await skiftPin('visible-42/abc:x', 'm1')
  const noegler = Object.keys((SecureStore as unknown as { __lager: Record<string, string> }).__lager)
  expect(noegler[0]).toMatch(/^jarvis:pinned:[A-Za-z0-9._-]+$/)
})

it('et ulæseligt lager koster ikke adgang til samtalen', async () => {
  ;(SecureStore.getItemAsync as jest.Mock).mockRejectedValueOnce(new Error('nede'))
  expect(await laesPins('s1')).toEqual([])
})

it('ignorerer skrald i lageret', async () => {
  ;(SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce('{ikke json')
  expect(await laesPins('s1')).toEqual([])
  ;(SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce('{"nej":1}')
  expect(await laesPins('s1')).toEqual([])
})

it('rydder', async () => {
  await skiftPin('s1', 'm1')
  await ryd('s1')
  expect(await laesPins('s1')).toEqual([])
})

it('viser pins i SAMTALENS rækkefølge, ikke i pin-rækkefølgen', () => {
  const beskeder = [{ id: 'a' }, { id: 'b' }, { id: 'c' }]
  expect(pinnedeIRaekkefoelge(beskeder, ['c', 'a'])).toEqual([{ id: 'a' }, { id: 'c' }])
})

it('tomt id gør ingenting', async () => {
  expect(await skiftPin('s1', '')).toEqual([])
})
