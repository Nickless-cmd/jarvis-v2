import { describe, it, expect, beforeEach } from 'vitest'
import { loadComposerHistory, pushComposerHistory, COMPOSER_HISTORY_KEY } from './Composer'

describe('composer besked-historik (pil op/ned)', () => {
  beforeEach(() => localStorage.removeItem(COMPOSER_HISTORY_KEY))

  it('gemmer + loader i rækkefølge (ældst først)', () => {
    pushComposerHistory('en')
    pushComposerHistory('to')
    expect(loadComposerHistory()).toEqual(['en', 'to'])
  })

  it('ignorerer tomme + trimmer', () => {
    pushComposerHistory('   ')
    pushComposerHistory('  hej  ')
    expect(loadComposerHistory()).toEqual(['hej'])
  })

  it('dedupliker samme besked lige efter hinanden', () => {
    pushComposerHistory('samme')
    pushComposerHistory('samme')
    pushComposerHistory('anden')
    pushComposerHistory('samme')
    expect(loadComposerHistory()).toEqual(['samme', 'anden', 'samme'])
  })

  it('tåler korrupt localStorage uden at kaste', () => {
    localStorage.setItem(COMPOSER_HISTORY_KEY, '{ikke json')
    expect(loadComposerHistory()).toEqual([])
    expect(() => pushComposerHistory('ok')).not.toThrow()
  })
})
