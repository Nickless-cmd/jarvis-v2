import { beskrivUdfald, normalisérUdfald } from './fladeHandling'

// Samme kontrakt som desk (`apps/jarvis-desk/src/lib/fladeHandling.ts`). Filen
// er kopieret, så testen er også: driver de to fra hinanden, er det her det
// skal gøre ondt — ikke i en telefon et halvt år senere.
describe('normalisérUdfald', () => {
  it('en tavs retur er IKKE succes — den er component_unavailable', () => {
    expect(normalisérUdfald(undefined)).toEqual({
      status: 'failed',
      kode: 'component_unavailable',
      besked: '',
    })
  })

  it('et tilfældigt tal fra en gammel provider bliver component_unavailable', () => {
    expect(normalisérUdfald(3).status).toBe('failed')
  })

  it('delivered bevares', () => {
    expect(normalisérUdfald({ status: 'delivered' })).toEqual({ status: 'delivered' })
  })

  it('ukendt fejlkode falder tilbage til tool_failed', () => {
    expect(normalisérUdfald({ status: 'failed', kode: 'noget-nyt' })).toEqual({
      status: 'failed',
      kode: 'tool_failed',
      besked: '',
    })
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
