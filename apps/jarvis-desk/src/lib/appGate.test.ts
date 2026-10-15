import { describe, expect, it } from 'vitest'
import { appGate } from './appGate'
import type { WhoAmI } from './api'

const bjorn: WhoAmI = { user_id: 'u1', display_name: 'Bjørn', role: 'owner' }

describe('appGate', () => {
  it('lukker igennem naar identity og status er i orden', () => {
    expect(appGate('ready', bjorn)).toBe('app')
  })

  // Regression 15/10-2026: AppImage'en kastede `Cannot read properties of null
  // (reading 'user_id')` fordi `identity={auth!}` blev laest foer whoami
  // svarede. I Electron er `authStatus` `undefined`, saa ingen af de gamle
  // guards matchede og grenen faldt igennem med `auth === null`.
  it('venter i stedet for at kaste naar Electron giver undefined og auth er null', () => {
    expect(appGate(undefined, null)).toBe('loading')
  })

  it('venter naar Electron giver undefined selv om auth endnu ikke er sat', () => {
    // Samme tilfaelde, skrevet som det faktisk optraeder: status er `undefined`,
    // ikke `'checking'` — derfor fangede den gamle guard det ikke.
    expect(appGate(undefined, null)).not.toBe('app')
  })

  it('lukker igennem i Electron naar identity ER kommet', () => {
    expect(appGate(undefined, bjorn)).toBe('app')
  })

  it('venter mens web-versionen spoerger', () => {
    expect(appGate('checking', null)).toBe('loading')
    expect(appGate('checking', bjorn)).toBe('loading')
  })

  it('venter ved idle — ogsaa en status uden identity', () => {
    expect(appGate('idle', null)).toBe('loading')
  })

  it('forklarer en forbindelsesfejl ogsaa naar vi aldrig fik en identity', () => {
    expect(appGate('offline', null)).toBe('offline')
    expect(appGate('offline', bjorn)).toBe('offline')
  })

  it('behandler en manglende identity som ventende, uanset status', () => {
    for (const status of ['checking', 'ready', 'idle', undefined] as const) {
      expect(appGate(status, null)).toBe('loading')
    }
  })
})
