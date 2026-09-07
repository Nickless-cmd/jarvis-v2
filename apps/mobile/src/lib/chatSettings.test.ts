import * as SecureStore from 'expo-secure-store'
import { laesIndstillinger, gemIndstillinger, tilStreamFelter, STANDARD } from './chatSettings'

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

it('standard er den SIKRE vej: spørg først, kun samtale-værktøjer', () => {
  expect(STANDARD.spoergFoerst).toBe(true)
  expect(STANDARD.vaerktoejer).toBe('samtale')
})

it('gemmer pr. samtale — én samtales valg lækker ikke til en anden', async () => {
  await gemIndstillinger('s1', { model: 'pro', stemme: true })
  expect((await laesIndstillinger('s1')).model).toBe('pro')
  expect((await laesIndstillinger('s2')).model).toBe('')
})

it('oversætter til de felter serveren faktisk forstår', () => {
  expect(tilStreamFelter({ ...STANDARD, vaerktoejer: 'fuldt', spoergFoerst: false }))
    .toEqual({ model: '', mode: 'code', approvalMode: 'trust' })
  expect(tilStreamFelter(STANDARD))
    .toEqual({ model: '', mode: 'chat', approvalMode: 'ask' })
})

it('tom per-chat-model betyder «som appen plejer», ikke «ingen model»', () => {
  expect(tilStreamFelter(STANDARD, 'deepseek-v4').model).toBe('deepseek-v4')
  expect(tilStreamFelter({ ...STANDARD, model: 'pro' }, 'deepseek-v4').model).toBe('pro')
})

it('skrald i lageret falder tilbage til standard', async () => {
  ;(SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce('{ikke json')
  expect(await laesIndstillinger('s1')).toEqual(STANDARD)
  ;(SecureStore.getItemAsync as jest.Mock).mockResolvedValueOnce('{"vaerktoejer":"vås"}')
  expect((await laesIndstillinger('s1')).vaerktoejer).toBe('samtale')
})

it('et ulæseligt lager vælter ikke skærmen', async () => {
  ;(SecureStore.getItemAsync as jest.Mock).mockRejectedValueOnce(new Error('nede'))
  expect(await laesIndstillinger('s1')).toEqual(STANDARD)
})

it('delvis opdatering bevarer resten', async () => {
  await gemIndstillinger('s1', { model: 'pro', stemme: true })
  const ny = await gemIndstillinger('s1', { stemme: false })
  expect(ny).toMatchObject({ model: 'pro', stemme: false })
})
