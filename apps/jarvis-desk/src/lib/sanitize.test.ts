import { describe, it, expect } from 'vitest'
import { safeLinkHref, safeImageSrc } from './sanitize'

describe('safeLinkHref', () => {
  it('allows http/https/mailto', () => {
    expect(safeLinkHref('https://example.com')).toBe('https://example.com')
    expect(safeLinkHref('http://x.dk')).toBe('http://x.dk')
    expect(safeLinkHref('mailto:a@b.dk')).toBe('mailto:a@b.dk')
  })
  it('blocks dangerous schemes', () => {
    expect(safeLinkHref('javascript:alert(1)')).toBeNull()
    expect(safeLinkHref('file:///etc/passwd')).toBeNull()
    expect(safeLinkHref('data:text/html,<script>')).toBeNull()
    expect(safeLinkHref('blob:abc')).toBeNull()
    expect(safeLinkHref('vbscript:x')).toBeNull()
  })
  it('blocks malformed URLs', () => {
    expect(safeLinkHref('not a url ::: http')).toBeNull()
    expect(safeLinkHref('')).toBeNull()
  })
  it('is case-insensitive on scheme', () => {
    expect(safeLinkHref('JavaScript:alert(1)')).toBeNull()
  })
})

describe('safeImageSrc', () => {
  it('allows https', () => {
    expect(safeImageSrc('https://cdn.x/img.png')).toBe('https://cdn.x/img.png')
  })
  it('allows backend attachment relative paths', () => {
    expect(safeImageSrc('/attachments/abc.png')).toBe('/attachments/abc.png')
  })
  it('blocks file: and data: by default', () => {
    expect(safeImageSrc('file:///x.png')).toBeNull()
    expect(safeImageSrc('data:image/png;base64,AAAA')).toBeNull()
  })
  it('blocks data:image/svg+xml (script vector)', () => {
    expect(safeImageSrc('data:image/svg+xml,<svg onload=alert(1)>')).toBeNull()
  })
})
