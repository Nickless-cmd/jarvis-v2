import { describe, it, expect } from 'vitest'
import { readFileSync, readdirSync } from 'node:fs'
import { resolve, join } from 'node:path'
import ts from 'typescript'

/**
 * Ét sted tegner kortet — og hver flade med en composer viser det.
 *
 * Fejlen var ikke at kortet var forkert. Det fandtes ÉT sted i hele desk
 * (`CodeView.tsx:1200`), saa paa chat-fladen var der ingenting. Det er samme
 * figur som godkendelses-lageret natten foer: spaerren var lavet rigtigt, men
 * ikke gjort til den eneste vej — og som genoptagelses-varslet samme morgen.
 *
 * AST, ikke grep: navnet staar ogsaa i import-linjer og kommentarer.
 */
const SRC = resolve(__dirname, '../..')
const VIEWS = join(SRC, 'views')

function tsxFiler(mappe: string): string[] {
  return readdirSync(mappe, { withFileTypes: true }).flatMap((d) => {
    const p = join(mappe, d.name)
    if (d.isDirectory()) return tsxFiler(p)
    return d.name.endsWith('.tsx') && !d.name.includes('.test.') ? [p] : []
  })
}

function jsxNavne(fil: string): string[] {
  const kilde = ts.createSourceFile(fil, readFileSync(fil, 'utf-8'),
    ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const ud: string[] = []
  const gaa = (n: ts.Node) => {
    if (ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n)) ud.push(n.tagName.getText())
    ts.forEachChild(n, gaa)
  }
  gaa(kilde)
  return ud
}

describe('godkendelses-kortet', () => {
  it('tegnes kun af GodkendelsesKort', () => {
    const syndere = tsxFiler(SRC)
      .filter((f) => !f.endsWith('GodkendelsesKort.tsx'))
      .filter((f) => jsxNavne(f).includes('ApprovalCard'))
      .map((f) => f.slice(SRC.length + 1))
    expect(syndere, 'et kort tegnes uden om den faelles komponent — saa kan en '
      + 'flade komme til at mangle det, praecis som chat-fladen gjorde').toEqual([])
  })

  it('vises paa hver flade der har en composer', () => {
    // En composer betyder at man kan bede om noget dér, og saa skal svaret
    // paa «maa jeg?» ogsaa kunne gives dér.
    const mangler = tsxFiler(VIEWS)
      .filter((f) => jsxNavne(f).includes('Composer'))
      .filter((f) => !jsxNavne(f).includes('GodkendelsesKort'))
      .map((f) => f.slice(VIEWS.length + 1))
    expect(mangler, 'en flade kan sende, men kan ikke svare paa en godkendelse '
      + '— saa ser den ud som om Jarvis er staaet af').toEqual([])
  })
})
