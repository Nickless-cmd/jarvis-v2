import { describe, it, expect } from 'vitest'
import { enforceStructure } from './enforceStructure'

// Spejler core/services/markdown_structure.py — Jarvis emitterer ~50% af svar
// UDEN newlines (alt inline med ` - `/`**X:**`). enforceStructure skal rekonstruere
// blokstruktur så live-visningen også bliver renderbar.
describe('enforceStructure — inline-markør-rekonstruktion', () => {
  it('inline bullets bliver en liste på egne linjer', () => {
    const out = enforceStructure('Her er punkterne: - et - to - tre')
    const lines = out.split('\n')
    expect(lines).toContain('- et')
    expect(lines).toContain('- to')
    expect(lines).toContain('- tre')
  })

  it('én enkelt tankestreg røres ikke', () => {
    const src = 'Det virker fint - næsten altid.'
    expect(enforceStructure(src)).toBe(src)
  })

  it('inline **Header:** bliver egen blok (promoveret til ## header)', () => {
    const out = enforceStructure('Intro tekst. **Hvad det er:** noget indhold bagefter')
    // Kolon-header på egen linje promoveres til en rigtig markdown-header.
    expect(out).toContain('## Hvad det er')
    const lines = out.split('\n')
    expect(lines.some((l) => l.trim() === '## Hvad det er')).toBe(true)
  })

  it('flerords **sætning.** bliver eget afsnit', () => {
    const out = enforceStructure('noget (ask/trust) **Det er chat + permissions.** Ingen plans her')
    expect(out).toContain('\n\n**Det er chat + permissions.**\n\n')
  })

  it('kort inline-emphasis brækkes IKKE', () => {
    const src = 'Det er **vigtigt!** at huske'
    expect(enforceStructure(src)).toBe(src)
  })

  it('kode-fence er beskyttet', () => {
    const out = enforceStructure('Kør:\n```\nfor x - y - z\n```\nog - a - b - c')
    expect(out).toContain('for x - y - z')
  })
})
