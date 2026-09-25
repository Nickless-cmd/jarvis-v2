import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ts from 'typescript'

/**
 * Vaerten maa ikke havne bag flade-kontakten.
 *
 * Det var praecis fejlen: spoergsmaalet laa i `ChatView`, som `App` kun
 * monterer naar `surface === 'chat'`. Bjoern sad paa kode-fladen, og varslet
 * blev aldrig hentet — i 11½ time, uden en eneste fejl nogen steder.
 *
 * AST, ikke grep: navnet staar ogsaa i import-linjen, og en grep ville bestaa
 * selv om elementet blev flyttet ind bag `surface === 'chat' &&`. Se
 * `source_guards_need_ast` — den fejl har jeg lavet foer.
 */
const KILDE = resolve(__dirname, '../../App.tsx')
const VAERT = 'GenoptagelsesVarselHost'

function flademarkoerOmkring(node: ts.Node): string | null {
  for (let n: ts.Node | undefined = node.parent; n; n = n.parent) {
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken) {
      const v = n.left.getText()
      if (v.includes('surface')) return v
    }
    if (ts.isConditionalExpression(n) && n.condition.getText().includes('surface')) {
      return n.condition.getText()
    }
  }
  return null
}

describe('App monterer varsel-vaerten', () => {
  const kilde = ts.createSourceFile(KILDE, readFileSync(KILDE, 'utf-8'),
    ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)

  const brug: ts.Node[] = []
  const gaa = (n: ts.Node) => {
    if ((ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n))
        && n.tagName.getText() === VAERT) brug.push(n)
    ts.forEachChild(n, gaa)
  }
  gaa(kilde)

  it('er monteret præcis ét sted', () => {
    expect(brug.length, `${VAERT} monteres ${brug.length} steder i App.tsx`).toBe(1)
  })

  it('er IKKE betinget af hvilken flade der vises', () => {
    const foerste = brug[0]
    expect(foerste, `${VAERT} monteres slet ikke i App.tsx`).toBeDefined()
    const bag = flademarkoerOmkring(foerste!)
    expect(bag, `${VAERT} ligger bag «${bag}» — saa spoerges der kun paa én flade, `
      + 'og det var netop fejlen der stod i 11½ time').toBeNull()
  })
})
