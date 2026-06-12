import { describe, it, expect } from 'vitest'
import { emojify } from './emojify'

describe('emojify', () => {
  it('konverterer almindelige emoticons', () => {
    expect(emojify('hej :)')).toBe('hej 🙂')
    expect(emojify('fedt ;) tak')).toBe('fedt 😉 tak')
    expect(emojify('haha :P')).toBe('haha 😛')
    expect(emojify('øv :(')).toBe('øv 🙁')
    expect(emojify('<3')).toBe('❤️')
  })
  it('rammer ikke URLs eller kode', () => {
    expect(emojify('se http://x.dk/p')).toBe('se http://x.dk/p')
    expect(emojify('dict[key]')).toBe('dict[key]')
  })
  it('konverterer ved tegnsætning', () => {
    expect(emojify('tak:).')).toBe('tak🙂.')
  })
})
