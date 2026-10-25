import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { describe, expect, it } from 'vitest'

const laes = (fil: string) => readFileSync(join(__dirname, fil), 'utf8')

describe('Chat/Code — fælles gulv mod composeren', () => {
  const css = laes('chat-viewport.css')

  it('holder toppen tæt og den samlede bundafstand på 8px', () => {
    expect(css).toMatch(/\.transcript\s*\{[\s\S]*?padding:\s*12px 24px 4px/)
    expect(css).toMatch(/linear-gradient\(to bottom, transparent 0, #000 16px/)
    expect(css).toMatch(/\.chatview \.composer,\s*\.codeview \.composer\s*\{[\s\S]*?margin:\s*4px auto 14px/)
  })

  it('holder Chat og Code på samme regel', () => {
    expect(css).toMatch(/\.chatview \.transcript,\s*\.codeview \.transcript/)
    expect(css).toMatch(/\.chatview \.composer,\s*\.codeview \.composer/)
  })
})
