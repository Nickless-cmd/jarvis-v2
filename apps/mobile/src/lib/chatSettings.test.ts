import * as SecureStore from 'expo-secure-store'
import { laesIndstillinger, gemIndstillinger, tilStreamFelter, STANDARD } from './chatSettings'

// Attrappen HAANDHAEVER SecureStores egen regel om noeglen. Den gjorde den
// ikke foer, og derfor kunne hele denne testfil vaere groen mens funktionen
// aldrig havde gemt noget i produktion: praefikset var 'jarvis:chatcfg:', og
// kolon er ugyldigt. En attrap der tager imod det virkeligheden afviser,
// maaler ingenting.
//
// Reglen er Expos: kun [A-Za-z0-9._-].
const GYLDIG_NOEGLE = /^[A-Za-z0-9._-]+$/

jest.mock('expo-secure-store', () => {
  const lager: Record<string, string> = {}
  const tjek = (k: string) => {
    if (!/^[A-Za-z0-9._-]+$/.test(k)) {
      throw new Error(`Invalid key "${k}" — SecureStore tillader kun [A-Za-z0-9._-]`)
    }
  }
  return {
    __lager: lager,
    getItemAsync: jest.fn(async (k: string) => { tjek(k); return lager[k] ?? null }),
    setItemAsync: jest.fn(async (k: string, v: string) => { tjek(k); lager[k] = v }),
    deleteItemAsync: jest.fn(async (k: string) => { tjek(k); delete lager[k] }),
  }
})

beforeEach(() => {
  const l = (SecureStore as unknown as { __lager: Record<string, string> }).__lager
  Object.keys(l).forEach((k) => delete l[k])
  jest.clearAllMocks()
})

it('standard er den SIKRE vej: spørg først, kun samtale-værktøjer', () => {
  expect(STANDARD.version).toBe(2)
  expect(STANDARD.spoergFoerst).toBe(true)
  expect(STANDARD.vaerktoejer).toBe('samtale')
  expect(STANDARD.thinkingMode).toBe('think')
  expect(STANDARD.researchMode).toBe('off')
})

it('gemmer pr. samtale — én samtales valg lækker ikke til en anden', async () => {
  const model = { model: 'pro', providerChoice: 'deepseek', label: 'Pro' }
  await gemIndstillinger('s1', { model, stemme: true, researchMode: 'on' })
  expect((await laesIndstillinger('s1')).model).toEqual(model)
  expect((await laesIndstillinger('s1')).researchMode).toBe('on')
  expect((await laesIndstillinger('s2')).model).toBeNull()
})

it('oversætter til de felter serveren faktisk forstår', () => {
  expect(tilStreamFelter({ ...STANDARD, vaerktoejer: 'fuldt', spoergFoerst: false }))
    .toEqual({
      model: '', providerChoice: '', mode: 'code', approvalMode: 'trust',
      thinkingMode: 'think', researchMode: false,
    })
  expect(tilStreamFelter(STANDARD))
    .toEqual({
      model: '', providerChoice: '', mode: 'chat', approvalMode: 'ask',
      thinkingMode: 'think', researchMode: false,
    })
})

it('sender model-id, provider og alle turn-controls atomisk', () => {
  const model = { model: 'deepseek-v4-flash', providerChoice: 'deepseek', label: 'Flash' }
  expect(tilStreamFelter({
    ...STANDARD, model, thinkingMode: 'fast', researchMode: 'on',
  })).toMatchObject({
    model: 'deepseek-v4-flash', providerChoice: 'deepseek',
    thinkingMode: 'fast', researchMode: true,
  })
})

it('bevarer member-modeller hvor provider vælges server-side', async () => {
  const model = { model: 'pro', providerChoice: '', label: 'Pro' }
  await gemIndstillinger('member-chat', { model })
  expect((await laesIndstillinger('member-chat')).model).toEqual(model)
})

it('migrerer v1 sikkert og gætter ikke provider fra et gammelt model-id', async () => {
  const lager = (SecureStore as unknown as { __lager: Record<string, string> }).__lager
  // Noeglen var 'jarvis:chatcfg:s1' indtil 12. sep 2026. At DENNE test bestod
  // med den er selve pointen: attrappen tog imod en noegle telefonen afviser.
  lager['jarvis.chatcfg.s1'] = JSON.stringify({ model: 'pro', stemme: true })
  expect(await laesIndstillinger('s1')).toMatchObject({
    version: 2, model: null, stemme: true, thinkingMode: 'think', researchMode: 'off',
  })
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
  const model = { model: 'pro', providerChoice: 'deepseek', label: 'Pro' }
  await gemIndstillinger('s1', { model, stemme: true })
  const ny = await gemIndstillinger('s1', { stemme: false })
  expect(ny).toMatchObject({ model, stemme: false })
})


// ── noeglen ──────────────────────────────────────────────────────────────

describe('noeglen overholder SecureStores regler', () => {
  it('gemmer og laeser den samme vaerdi tilbage', async () => {
    await gemIndstillinger('chat-e58f16c561a64747b8da583302fbc604', { spoergFoerst: false })
    const igen = await laesIndstillinger('chat-e58f16c561a64747b8da583302fbc604')
    expect(igen.spoergFoerst).toBe(false)
  })

  it('hver skreven noegle er gyldig', async () => {
    await gemIndstillinger('chat-abc123', { stemme: true })
    const kald = (SecureStore.setItemAsync as jest.Mock).mock.calls
    expect(kald.length).toBeGreaterThan(0)
    for (const [k] of kald) expect(String(k)).toMatch(GYLDIG_NOEGLE)
  })

  it('et sessionId med ugyldige tegn giver stadig en gyldig noegle', async () => {
    await gemIndstillinger('chat:med/skraa og mellemrum', { stemme: true })
    const kald = (SecureStore.setItemAsync as jest.Mock).mock.calls
    for (const [k] of kald) expect(String(k)).toMatch(GYLDIG_NOEGLE)
  })

  it('en mislykket skrivning melder IKKE succes', async () => {
    // Den tavse catch returnerede den nye vaerdi uanset. Saa saa UI'et rigtigt
    // ud, og fejlen var usynlig indtil naeste app-start.
    const sid = 'chat-fejl'
    await gemIndstillinger(sid, { spoergFoerst: false })
    ;(SecureStore.setItemAsync as jest.Mock).mockRejectedValueOnce(new Error('disk fuld'))
    const svar = await gemIndstillinger(sid, { spoergFoerst: true })
    expect(svar.spoergFoerst).toBe(false)
  })
})
