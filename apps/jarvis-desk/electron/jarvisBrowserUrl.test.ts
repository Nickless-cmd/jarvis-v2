import { describe, it, expect, vi } from 'vitest'

// jarvisBrowser importerer electron. Vi tester KUN adressetydningen, som er
// ren tekst — resten af modulet roeres ikke af denne mock.
vi.mock('electron', () => ({
  WebContentsView: class {},
  BrowserWindow: class {},
  shell: { openExternal: vi.fn() },
}))

const { tydUrl } = await import('./jarvisBrowser')

/**
 * Hvad en adresselinje goer ved det man taster.
 *
 * Det her er den eneste vej fra tastatur til webvisning, og den skal ikke
 * kunne overraske: «github.com» maa ikke blive en soegning, og en soegning
 * maa ikke blive til et haabloest https://-opslag paa et vaertsnavn der ikke
 * findes. En fejlside ser ud som om browseren er i stykker.
 */
describe('tydUrl', () => {
  it('lader en hel adresse staa', () => {
    expect(tydUrl('https://github.com/x?y=1#z')).toBe('https://github.com/x?y=1#z')
    expect(tydUrl('http://10.0.0.39:8000/api')).toBe('http://10.0.0.39:8000/api')
    expect(tydUrl('about:blank')).toBe('about:blank')
    expect(tydUrl('file:///tmp/x.html')).toBe('file:///tmp/x.html')
  })

  it('saetter https paa noget der ligner et vaertsnavn', () => {
    expect(tydUrl('github.com')).toBe('https://github.com')
    expect(tydUrl('docs.example.co.uk/side')).toBe('https://docs.example.co.uk/side')
    expect(tydUrl('  github.com  ')).toBe('https://github.com')
  })

  it('kender localhost og en port — ellers var udvikling umulig herinde', () => {
    expect(tydUrl('localhost:5174')).toBe('https://localhost:5174')
    expect(tydUrl('example.dk:8443/x')).toBe('https://example.dk:8443/x')
  })

  it('kalder ikke javascript: — den bliver en soegning som alt andet ukendt', () => {
    // Taster man (eller indsaetter man) javascript:..., skal det IKKE koere i
    // den aabne side. Reglen om «://» goer den til almindelig tekst.
    expect(tydUrl('javascript:alert(1)')).toBe('https://duckduckgo.com/?q=javascript%3Aalert(1)')
  })

  it('soeger naar det ikke ligner et vaertsnavn', () => {
    expect(tydUrl('hvad er en webcontentsview')).toBe(
      'https://duckduckgo.com/?q=hvad%20er%20en%20webcontentsview')
    // Ét ord uden punktum er ogsaa en soegning, ikke et vaertsnavn.
    expect(tydUrl('webcontentsview')).toBe('https://duckduckgo.com/?q=webcontentsview')
  })

  it('giver about:blank paa tomt felt i stedet for at soege efter ingenting', () => {
    expect(tydUrl('')).toBe('about:blank')
    expect(tydUrl('   ')).toBe('about:blank')
  })
})
