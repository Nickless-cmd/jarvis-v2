import { describe, it, expect } from 'vitest'
import {
  PASTE_CHAR_THRESHOLD,
  PASTE_LINE_THRESHOLD,
  buildPasteReference,
  parsePasteReference,
  pasteLineCount,
  shouldExternalizePaste,
} from './pasteStore'

describe('pasteStore threshold logic', () => {
  it('counts lines without over-counting a trailing newline', () => {
    expect(pasteLineCount('')).toBe(0)
    expect(pasteLineCount('one line')).toBe(1)
    expect(pasteLineCount('a\nb\nc')).toBe(3)
    expect(pasteLineCount('a\nb\n')).toBe(2)
  })

  it('does NOT externalize small pastes', () => {
    expect(shouldExternalizePaste('kort tekst')).toBe(false)
    expect(shouldExternalizePaste('a\n'.repeat(PASTE_LINE_THRESHOLD))).toBe(false)
    expect(shouldExternalizePaste('')).toBe(false)
  })

  it('externalizes when over the line threshold', () => {
    const many = Array.from({ length: PASTE_LINE_THRESHOLD + 1 }, (_, i) => `line ${i}`).join('\n')
    expect(shouldExternalizePaste(many)).toBe(true)
  })

  it('externalizes when over the char threshold', () => {
    expect(shouldExternalizePaste('x'.repeat(PASTE_CHAR_THRESHOLD + 1))).toBe(true)
  })
})

describe('pasteStore reference format', () => {
  it('builds the reference string backend-compatibly', () => {
    expect(buildPasteReference('deadbeefdeadbeef', 42)).toBe('[paste:deadbeefdeadbeef +42 linjer]')
  })

  it('build/parse are symmetric', () => {
    const ref = buildPasteReference('abc123', 10)
    expect(parsePasteReference(ref)).toEqual({ pasteId: 'abc123', lineCount: 10 })
  })

  it('parses a reference embedded in surrounding text', () => {
    const parsed = parsePasteReference('se her:\n[paste:zz99 +7 linjer]\ntak')
    expect(parsed).toEqual({ pasteId: 'zz99', lineCount: 7 })
  })

  it('returns null for non-references', () => {
    expect(parsePasteReference('helt normal besked')).toBeNull()
    expect(parsePasteReference('')).toBeNull()
  })
})
