import { describe, it, expect, beforeEach } from 'vitest'
import { PERM_KEY, MODEL_KEY, PROV_KEY, readModelPrefs } from './composerPrefs'

describe('composerPrefs', () => {
  beforeEach(() => localStorage.clear())

  it('exposes stable storage keys', () => {
    expect(PERM_KEY).toBe('jarvis-desk:permission')
    expect(MODEL_KEY).toBe('jarvis-desk:model')
    expect(PROV_KEY).toBe('jarvis-desk:provChoice')
  })

  it('defaults model to empty and provider to deepseek', () => {
    expect(readModelPrefs()).toEqual({ model: '', providerChoice: 'deepseek' })
  })

  it('reads stored values', () => {
    localStorage.setItem(MODEL_KEY, 'pro')
    localStorage.setItem(PROV_KEY, 'glm')
    expect(readModelPrefs()).toEqual({ model: 'pro', providerChoice: 'glm' })
  })
})
