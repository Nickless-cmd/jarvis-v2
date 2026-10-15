import { beforeEach, describe, expect, it } from 'vitest'
import { RAEKKE_KEY, readRaekkevisning, writeRaekkevisning } from './visningsPref'

describe('Code Mode row preference', () => {
  beforeEach(() => localStorage.clear())

  it('preserves the legacy key and value', () => {
    expect(RAEKKE_KEY).toBe('jarvis-desk:raekkevisning')
    writeRaekkevisning(true)
    expect(readRaekkevisning()).toBe(true)
    expect(localStorage.getItem(RAEKKE_KEY)).toBe('1')
  })
})
