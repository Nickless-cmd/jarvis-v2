import { describe, it, expect } from 'vitest'
import { createLocationResolver, FEJL_TTL_MS, OK_TTL_MS } from './locationResolver'
import type { DeskLocationPayload, LocationMode } from './deskLocation'

const SVENDBORG: DeskLocationPayload = { lat: 55.06, lon: 10.6, label: 'Svendborg', source: 'ip', precision: 'city' }

function opsaet(mode: LocationMode = 'browser', svar: Array<DeskLocationPayload | null> = []) {
  const s = { mode, nu: 1_000_000, kald: [] as LocationMode[], svar: [...svar] }
  const resolve = createLocationResolver({
    loadMode: () => s.mode,
    getLocation: async (m) => { s.kald.push(m); return s.svar.length ? (s.svar.shift() as DeskLocationPayload | null) : null },
    now: () => s.nu,
  })
  return { s, resolve }
}

describe('createLocationResolver', () => {
  it('et lykkedes-svar caches i OK_TTL_MS', async () => {
    const { s, resolve } = opsaet('ip', [SVENDBORG])
    expect(await resolve()).toEqual(SVENDBORG)
    s.nu += OK_TTL_MS - 1
    expect(await resolve()).toEqual(SVENDBORG)
    expect(s.kald).toEqual(['ip'])
    s.nu += 1
    await resolve()
    expect(s.kald).toEqual(['ip', 'ip'])
  })

  it('en FEJL caches også: pinget gentager ikke et opslag der netop fejlede (geo/reverse-storm 14/11-2026)', async () => {
    const { s, resolve } = opsaet('browser', [null])
    expect(await resolve()).toBeUndefined()
    for (let i = 0; i < 20; i++) { s.nu += 5_000; await resolve() }   // 100 s med et ping hvert 5. s
    expect(s.kald).toEqual(['browser'])
  })

  it('efter FEJL_TTL_MS prøves der igen, og en succes erstatter fejlen', async () => {
    const { s, resolve } = opsaet('browser', [null, SVENDBORG])
    expect(await resolve()).toBeUndefined()
    s.nu += FEJL_TTL_MS
    expect(await resolve()).toEqual(SVENDBORG)
    expect(s.kald).toHaveLength(2)
  })

  it('en fejl sletter ikke et tidligere godt sted', async () => {
    const { s, resolve } = opsaet('ip', [SVENDBORG, null])
    await resolve()
    s.nu += OK_TTL_MS
    expect(await resolve()).toEqual(SVENDBORG)      // opslaget fejlede, men vi beholder stedet
    s.nu += 5_000
    expect(await resolve()).toEqual(SVENDBORG)
    expect(s.kald).toHaveLength(2)                  // og forsøger ikke igen med det samme
  })

  it('skift af metode rammer ikke den gamle metodes cache (heller ikke en fejl)', async () => {
    const { s, resolve } = opsaet('browser', [null, SVENDBORG])
    expect(await resolve()).toBeUndefined()
    s.mode = 'ip'
    expect(await resolve()).toEqual(SVENDBORG)
    expect(s.kald).toEqual(['browser', 'ip'])
  })

  it('off sender {} ÉN gang, derefter undefined, og kalder aldrig getLocation', async () => {
    const { s, resolve } = opsaet('off')
    expect(await resolve()).toEqual({})
    expect(await resolve()).toBeUndefined()
    expect(s.kald).toEqual([])
  })

  it('off og så tændt igen henter forfra og sender {} igen ved næste off', async () => {
    const { s, resolve } = opsaet('ip', [SVENDBORG, SVENDBORG])
    await resolve()
    s.mode = 'off'
    expect(await resolve()).toEqual({})
    s.mode = 'ip'
    expect(await resolve()).toEqual(SVENDBORG)       // cachen blev ryddet af off
    s.mode = 'off'
    expect(await resolve()).toEqual({})
  })

  it('samtidige kald deler ét opslag', async () => {
    const s = { n: 0 }
    let frigiv: (v: DeskLocationPayload | null) => void = () => {}
    const resolve = createLocationResolver({
      loadMode: () => 'browser',
      getLocation: () => { s.n++; return new Promise((r) => { frigiv = r }) },
      now: () => 1,
    })
    const a = resolve(); const b = resolve(); const c = resolve()
    frigiv(SVENDBORG)
    expect(await Promise.all([a, b, c])).toEqual([SVENDBORG, SVENDBORG, SVENDBORG])
    expect(s.n).toBe(1)
  })
})
