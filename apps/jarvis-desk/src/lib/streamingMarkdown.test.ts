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
})
