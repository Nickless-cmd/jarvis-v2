import { describeUploadError } from './uploadError'

describe('describeUploadError', () => {
  it('viser serverens konkrete begrundelse', () => {
    expect(describeUploadError({ detail: 'Arkivet blev afvist: sti peger opad (..)' }))
      .toBe(' — Arkivet blev afvist: sti peger opad (..)')
  })

  it('graver detail ud af et JSON-svar i message', () => {
    const e = new Error(JSON.stringify({ detail: 'Upload afvist af malware-scan: Eicar' }))
    expect(describeUploadError(e)).toBe(' — Upload afvist af malware-scan: Eicar')
  })

  it('bruger teksten som den er naar den ikke er JSON', () => {
    expect(describeUploadError(new Error('netværksfejl'))).toBe(' — netværksfejl')
  })

  it('giver tom streng naar der intet er at sige', () => {
    expect(describeUploadError(null)).toBe('')
    expect(describeUploadError({})).toBe('')
    expect(describeUploadError(new Error(''))).toBe('')
  })
})
