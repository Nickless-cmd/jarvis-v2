import { parseModelChoice } from './sessionStore'

describe('parseModelChoice', () => {
  it('parser et gyldigt valg', () => {
    const raw = JSON.stringify({ model: 'pro', providerChoice: '', label: 'Pro' })
    expect(parseModelChoice(raw)).toEqual({ model: 'pro', providerChoice: '', label: 'Pro' })
  })
  it('null ved null/tom', () => {
    expect(parseModelChoice(null)).toBeNull()
    expect(parseModelChoice('')).toBeNull()
  })
  it('null ved malformet JSON', () => {
    expect(parseModelChoice('{ ikke json')).toBeNull()
  })
  it('null ved manglende felter', () => {
    expect(parseModelChoice(JSON.stringify({ model: 'pro' }))).toBeNull()
  })
})
