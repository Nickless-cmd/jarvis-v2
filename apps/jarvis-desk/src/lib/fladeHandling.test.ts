import { describe, expect, it } from 'vitest'
import { beskrivUdfald, normalisérUdfald } from './fladeHandling'

describe('normalisérUdfald', () => {
  it('en tavs retur er IKKE succes — den er component_unavailable', () => {
    // Den vigtigste regel i filen. En provider der glemmer at svare må ikke
    // se ud som om nogen lyttede; ellers er udfaldet værre end ingen udfald.
    expect(normalisérUdfald(undefined)).toEqual({
      status: 'failed',
      kode: 'component_unavailable',
      besked: '',
    })
  })

  it('et tilfældigt tal fra en gammel provider bliver component_unavailable', () => {
    // `set.push(t)` returnerer et tal. En mock der gør det påstår intet om
    // produktionen, og må ikke læses som «delivered».
    expect(normalisérUdfald(3).status).toBe('failed')
  })

  it('delivered bevares', () => {
    expect(normalisérUdfald({ status: 'delivered' })).toEqual({ status: 'delivered' })
  })

  it('ukendt fejlkode falder tilbage til tool_failed', () => {
    const u = normalisérUdfald({ status: 'failed', kode: 'noget-nyt' })
    expect(u).toEqual({ status: 'failed', kode: 'tool_failed', besked: '' })
  })

  it('en kendt fejlkode bevares med sin besked', () => {
    const u = normalisérUdfald({ status: 'failed', kode: 'empty_action', besked: 'tom' })
    expect(u).toEqual({ status: 'failed', kode: 'empty_action', besked: 'tom' })
  })
})

describe('beskrivUdfald', () => {
  it('delivered siger intet — turen fortsætter af sig selv i tråden', () => {
    expect(beskrivUdfald({ status: 'delivered' })).toBe('')
  })

  it('hver fejlkode har sin egen sætning', () => {
    const s = [
      beskrivUdfald({ status: 'failed', kode: 'component_unavailable', besked: '' }),
      beskrivUdfald({ status: 'failed', kode: 'empty_action', besked: '' }),
      beskrivUdfald({ status: 'failed', kode: 'tool_failed', besked: '' }),
    ]
    expect(new Set(s).size).toBe(3)
    for (const x of s) expect(x.length).toBeGreaterThan(0)
  })
})
