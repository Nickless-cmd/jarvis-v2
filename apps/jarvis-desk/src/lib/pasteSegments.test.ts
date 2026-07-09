import { describe, it, expect } from 'vitest'
import { hasPasteReference, splitPasteSegments } from './pasteSegments'

describe('pasteSegments', () => {
  it('returns a single text segment when there is no reference', () => {
    expect(splitPasteSegments('helt normal besked')).toEqual([
      { kind: 'text', text: 'helt normal besked' },
    ])
  })

  it('splits text around a paste reference', () => {
    const segs = splitPasteSegments('review dette:\n[paste:abc123 +42 linjer]\ntak')
    expect(segs).toEqual([
      { kind: 'text', text: 'review dette:\n' },
      { kind: 'paste', pasteId: 'abc123', lineCount: 42 },
      { kind: 'text', text: '\ntak' },
    ])
  })

  it('handles multiple references', () => {
    const segs = splitPasteSegments('[paste:a1 +3 linjer] og [paste:b2 +5 linjer]')
    expect(segs.filter((s) => s.kind === 'paste')).toEqual([
      { kind: 'paste', pasteId: 'a1', lineCount: 3 },
      { kind: 'paste', pasteId: 'b2', lineCount: 5 },
    ])
  })

  it('detects presence of a reference', () => {
    expect(hasPasteReference('x [paste:zz +1 linjer] y')).toBe(true)
    expect(hasPasteReference('ingen reference her')).toBe(false)
  })
})
