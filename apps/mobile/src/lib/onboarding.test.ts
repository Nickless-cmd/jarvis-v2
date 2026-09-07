import * as SecureStore from 'expo-secure-store'
import { TRIN, resterendeTrin, statusFor, erGennemfoert, markerGennemfoert } from './onboarding'

jest.mock('expo-secure-store', () => {
  const lager: Record<string, string> = {}
  return {
    __lager: lager,
    getItemAsync: jest.fn(async (k: string) => lager[k] ?? null),
    setItemAsync: jest.fn(async (k: string, v: string) => { lager[k] = v }),
  }
})

beforeEach(() => {
  const l = (SecureStore as unknown as { __lager: Record<string, string> }).__lager
  Object.keys(l).forEach((k) => delete l[k])
  jest.clearAllMocks()
})

it('push kommer først — uden den er halvdelen af appen stum', () => {
  expect(TRIN[0]?.tilladelse).toBe('push')
})

it('lokation kommer sidst — mest indgribende, mindst nødvendig', () => {
  expect(TRIN[TRIN.length - 1]?.tilladelse).toBe('lokation')
})

it('hvert trin siger HVORFOR og hvad man mister — ikke bare hvad der spørges om', () => {
  for (const t of TRIN) {
    expect(t.hvorfor.length).toBeGreaterThan(20)
    expect(t.udenDen.length).toBeGreaterThan(15)
  }
})

it('spørger ikke om noget der allerede er givet', () => {
  const r = resterendeTrin(['push', 'kamera'])
  expect(r.map((t) => t.tilladelse)).toEqual(['mikrofon', 'lokation'])
})

it('tæller «N af M» ud fra de RESTERENDE, ikke ud fra alle fire', () => {
  const r = resterendeTrin(['push'])
  expect(statusFor(r, 0)).toMatchObject({ nummer: 1, ialt: 3, faerdig: false })
  expect(statusFor(r, 2)).toMatchObject({ nummer: 3, ialt: 3 })
})

it('er færdig når man er igennem — også hvis der intet var at spørge om', () => {
  expect(statusFor(resterendeTrin(['push', 'mikrofon', 'kamera', 'lokation']), 0).faerdig).toBe(true)
  expect(statusFor(TRIN, TRIN.length).faerdig).toBe(true)
})

it('vises kun én gang', async () => {
  expect(await erGennemfoert()).toBe(false)
  await markerGennemfoert()
  expect(await erGennemfoert()).toBe(true)
})

it('et ulæseligt lager springer guiden over frem for at gentage den ved hver start', async () => {
  ;(SecureStore.getItemAsync as jest.Mock).mockRejectedValueOnce(new Error('nede'))
  expect(await erGennemfoert()).toBe(true)
})
