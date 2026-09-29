import { describe, it, expect } from 'vitest'
import { stabilizeStreamingMarkdown } from './streamingMarkdown'

describe('stabilizeStreamingMarkdown', () => {
  it('holds back an unclosed code fence', () => {
    const out = stabilizeStreamingMarkdown('tekst\n```js\nconst x')
    expect(out).toBe('tekst')
  })
  it('renders a closed code fence fully', () => {
    const md = 'tekst\n```js\nconst x = 1\n```'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('passes through plain text unchanged', () => {
    expect(stabilizeStreamingMarkdown('bare tekst')).toBe('bare tekst')
  })
  it('klipper ikke prosa med inline backticks', () => {
    const md = 'Her er et eksempel. Brug ``` for kode. Det er smart.'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('tre backticks inde i en fire-backtick fence lukker den ikke', () => {
    const md = '````md\nHer viser jeg ```\nkode\n````'
    expect(stabilizeStreamingMarkdown(md)).toBe(md)
  })
  it('genkender både åbne og lukkede tilde-fences', () => {
    expect(stabilizeStreamingMarkdown('Før\n~~~js\nconst x = 1')).toBe('Før')
    const lukket = 'Før\n~~~js\nconst x = 1\n~~~'
    expect(stabilizeStreamingMarkdown(lukket)).toBe(lukket)
  })
  it('kortere eller forkert tegn kan ikke lukke en fence', () => {
    expect(stabilizeStreamingMarkdown('Før\n````js\n```\n~~~')).toBe('Før')
  })
})
