import { describe, it, expect } from 'vitest'
import { behold, klausul, politikFor, klipLangeLinjer, MAX_LINJE_TEGN } from './udeladelse'

/**
 * Et langt vaerktoejs-resultat skal kunne SES at vaere klippet, og det rigtige
 * skal blive tilbage (spec punkt 5).
 *
 * Bjoern 30/9-2026: daempet klausul, hoved+hale for shell, kun hoved for
 * fil-laesning.
 */

const linjer = (n: number) => Array.from({ length: n }, (_, i) => `l${i}`).join('\n')

describe('politikken pr. værktøj', () => {
  it('shell beholder en HALE — exit-koden og fejlen står til sidst', () => {
    for (const n of ['bash', 'operator_bash', 'bash_session_run']) {
      expect(politikFor(n).hale, n).toBeGreaterThan(0)
    }
  })

  it('fil-læsning beholder INGEN hale — man læser forfra', () => {
    for (const n of ['read_file', 'operator_read_file', 'read_attachment']) {
      expect(politikFor(n).hale, n).toBe(0)
    }
  })

  it('et ukendt værktøj får standarden og lover ikke noget om halen', () => {
    const p = politikFor('noget_helt_andet')
    expect(p.hale).toBe(0)
    expect(p.hoved).toBeGreaterThan(0)
  })

  it('tomt eller whitespace-navn crasher ikke', () => {
    expect(politikFor('').hoved).toBeGreaterThan(0)
    expect(politikFor('  bash  ').hale).toBeGreaterThan(0)
  })

  it('hver politik har en vejledning — en klausul uden vej videre er en blokade', () => {
    for (const n of ['bash', 'read_file', 'ukendt']) {
      expect(politikFor(n).vejledning.length, n).toBeGreaterThan(0)
    }
  })
})

describe('behold', () => {
  const p = { hoved: 3, hale: 2, vejledning: 'v' }

  it('klipper IKKE når der ikke er noget at spare', () => {
    // Praecis hoved+hale linjer: der er intet at udelade, og en klausul om
    // «0 linjer udeladt» ville vaere stoej med en paastand i.
    const t = linjer(5)
    expect(behold(t, p)).toEqual({ tekst: t, hoved: t, hale: '', udeladt: 0, ialt: 5, klippet: false })
  })

  it('én linje over grænsen klipper', () => {
    const r = behold(linjer(6), p)
    expect(r.klippet).toBe(true)
    expect(r.udeladt).toBe(1)
    expect(r.tekst).toBe('l0\nl1\nl2\nl4\nl5')
  })

  it('beholder hoved OG hale, og tæller det udeladte rigtigt', () => {
    const r = behold(linjer(100), p)
    expect(r).toEqual({ tekst: 'l0\nl1\nl2\nl98\nl99', hoved: 'l0\nl1\nl2', hale: 'l98\nl99',
                       udeladt: 95, ialt: 100, klippet: true })
  })

  it('uden hale beholdes kun hovedet', () => {
    const r = behold(linjer(100), { hoved: 3, hale: 0, vejledning: 'v' })
    expect(r.tekst).toBe('l0\nl1\nl2')
    expect(r.udeladt).toBe(97)
  })

  it('tom tekst og ét-linjers tekst klippes ikke', () => {
    expect(behold('', p).klippet).toBe(false)
    expect(behold('kun én', p)).toEqual({ tekst: 'kun én', hoved: 'kun én', hale: '',
                                         udeladt: 0, ialt: 1, klippet: false })
  })

  it('negative tal i politikken behandles som 0', () => {
    const r = behold(linjer(10), { hoved: -5, hale: -5, vejledning: 'v' })
    expect(r.tekst).toBe('')
    expect(r.udeladt).toBe(10)
  })
})

describe('klausulen', () => {
  it('siger tallet, hvor, og hvad man gør', () => {
    const p = politikFor('bash')
    const u = behold(linjer(2000), p)
    const k = klausul(u, p)
    expect(k).toContain('1.968')          // dansk tusindtalsseparator
    expect(k).toContain('i midten')
    expect(k).toContain('tail')
  })

  it('siger «til sidst» når der ingen hale er — ikke «i midten»', () => {
    // Uden hale ER der ikke en midte. Ordet skal svare til det man ser.
    const p = politikFor('read_file')
    const k = klausul(behold(linjer(500), p), p)
    expect(k).toContain('til sidst')
    expect(k).not.toContain('i midten')
  })

  it('bøjer ental', () => {
    const p = { hoved: 3, hale: 2, vejledning: 'v' }
    expect(klausul(behold(linjer(6), p), p)).toContain('1 linje udeladt')
    expect(klausul(behold(linjer(7), p), p)).toContain('2 linjer udeladt')
  })

  it('er TOM når intet blev udeladt', () => {
    const p = { hoved: 3, hale: 2, vejledning: 'v' }
    expect(klausul(behold(linjer(4), p), p)).toBe('')
  })
})

describe('en enkelt meget lang linje', () => {
  it('klippes, for linje-tællingen ser den som én', () => {
    // Et base64-blob eller en minificeret fil er én linje. Uden det her ville
    // udeladelses-laget lade hele skaermen fylde med den.
    const blob = 'x'.repeat(MAX_LINJE_TEGN + 500)
    const ud = klipLangeLinjer(`før\n${blob}\nefter`)
    expect(ud.split('\n')[0]).toBe('før')
    expect(ud.split('\n')[2]).toBe('efter')
    expect(Array.from(ud.split('\n')[1]!).length).toBe(MAX_LINJE_TEGN)
  })

  it('rører ikke en tekst der er kort nok', () => {
    expect(klipLangeLinjer('a\nb\nc')).toBe('a\nb\nc')
  })

  it('bryder ikke et emoji på klippet', () => {
    const s = 'a'.repeat(MAX_LINJE_TEGN - 2) + '👍' + 'b'.repeat(50)
    const ud = klipLangeLinjer(s)
    const ensom = /[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]/
    expect(ud).not.toMatch(ensom)
  })
})
