import { describe, it, expect } from 'vitest'
import { scanFences, openingFence, closingFence } from './fenceScanner'

/**
 * Verifikation af spec punkt 9, akse 1 (30/9-2026).
 *
 * «Verificér» betyder ikke «læs koden og sig ja». `fenceScanner.ts` havde
 * INGEN test — aksen var antaget. Kant-tilfaeldene nedenfor er speccens egne,
 * hver med den mutation den skal fange.
 *
 * Hvorfor det betyder noget: scanneren afgoer hvad stabiliseringen og
 * struktur-filteret tror er kode. Tager den fejl om en aaben fence, kan
 * rendererens tekst forsvinde midt i et svar.
 */

const T = '```'

describe('åbnende fence', () => {
  it('kender backtick og tilde', () => {
    expect(openingFence(T)).toEqual({ marker: '`', length: 3 })
    expect(openingFence('~~~')).toEqual({ marker: '~', length: 3 })
  })

  it('sproget må komme EFTER markøren — det er den almindelige form', () => {
    expect(openingFence(T + 'bash')).toEqual({ marker: '`', length: 3 })
  })

  it('op til tre mellemrum er stadig top-level; fire er indrykket kode', () => {
    expect(openingFence('   ' + T)).not.toBeNull()
    expect(openingFence('    ' + T)).toBeNull()
  })

  it('inline backticks er PROSA, ikke en fence', () => {
    // «brug `ls` her» må aldrig åbne en kodeblok.
    expect(openingFence('brug `ls` her')).toBeNull()
    expect(openingFence(T + 'js `x`')).toBeNull()
  })

  it('to backticks er ikke nok', () => {
    expect(openingFence('``')).toBeNull()
  })
})

describe('lukkende fence', () => {
  const aaben = { marker: '`' as const, length: 3 }

  it('en KORTERE markør lukker ikke', () => {
    // Ellers kunne to backticks i prosa lukke en åben blok, og resten af
    // svaret ville skifte betydning midt i en streaming.
    expect(closingFence('``', aaben)).toBe(false)
    expect(closingFence(T, aaben)).toBe(true)
    expect(closingFence('````', aaben)).toBe(true)
  })

  it('en ANDEN markør lukker ikke', () => {
    expect(closingFence('~~~', aaben)).toBe(false)
  })

  it('tekst efter markøren lukker ikke', () => {
    expect(closingFence(T + 'js', aaben)).toBe(false)
    expect(closingFence(T + '  ', aaben)).toBe(true)   // kun blanktegn er ok
  })
})

describe('scanFences', () => {
  it('en lukket fence markeres lukket og ender ved sin lukkelinje', () => {
    const md = `før\n${T}js\nkode\n${T}\nefter`
    const s = scanFences(md)
    expect(s).toHaveLength(1)
    expect(s[0]!.closed).toBe(true)
    expect(md.slice(s[0]!.start, s[0]!.end)).toBe(`${T}js\nkode\n${T}`)
  })

  it('en fence der ALDRIG lukkes beskyttes frem til EOF', () => {
    // Det er den almindelige tilstand under streaming: halvdelen af koden er
    // kommet. Frøs vi den som lukket, ville resten af svaret blive tolket som
    // prosa i samme øjeblik den næste bid kom.
    const md = `før\n${T}py\nprint(1)\nprint(2)`
    const s = scanFences(md)
    expect(s).toHaveLength(1)
    expect(s[0]!.closed).toBe(false)
    expect(s[0]!.end).toBe(md.length)
  })

  it('en bid der slutter midt i markøren lukker IKKE', () => {
    // To af tre backticks. Speccens første kant-tilfælde.
    const md = `${T}sh\nls\n\`\``
    expect(scanFences(md)[0]!.closed).toBe(false)
  })

  it('sproget angivet efter åbningen ændrer ikke hvornår den lukker', () => {
    const md = `${T}typescript\nconst a = 1\n${T}`
    expect(scanFences(md)[0]!.closed).toBe(true)
  })

  it('en fence indrykket FIRE mellemrum er ikke top-level', () => {
    // Indlejret i en liste. Behandlede vi den som top-level, ville
    // stabiliseringen fryse listen som kode.
    expect(scanFences(`- punkt\n    ${T}\n    kode\n    ${T}`)).toHaveLength(0)
  })

  it('to fences efter hinanden findes begge', () => {
    const md = `${T}\na\n${T}\ntekst\n${T}\nb\n${T}`
    const s = scanFences(md)
    expect(s).toHaveLength(2)
    expect(s.every((x) => x.closed)).toBe(true)
  })

  it('tilde-fence lukkes ikke af backticks', () => {
    const md = `~~~\nkode\n${T}\nmere`
    const s = scanFences(md)
    expect(s[0]!.closed).toBe(false)
  })

  it('prosa uden fences giver ingen spans', () => {
    expect(scanFences('bare tekst med `inline` kode')).toEqual([])
    expect(scanFences('')).toEqual([])
  })

  it('offsets peger på den RIGTIGE tekst — ikke bare på et tal', () => {
    // En off-by-one her ville klippe en linje af blokken, og det ses først
    // som «koden mangler sin første linje».
    const md = `linje et\n${T}js\nx\n${T}\nhale`
    const s = scanFences(md)[0]!
    expect(md.slice(s.start, s.start + 3)).toBe(T)
    expect(md.slice(s.end - 3, s.end)).toBe(T)
  })
})
