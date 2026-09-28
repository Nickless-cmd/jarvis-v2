import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import * as ts from 'typescript'

/**
 * Genoptagelses-varslet spørger inde fra `ChatScreen`. Det holder KUN så
 * længe `App` faktisk har `ChatScreen` monteret hele tiden.
 *
 * I desk var præcis den antagelse forkert: spørgsmålet lå i `ChatView`, som
 * `App` kun monterer når `surface === 'chat'`. Bjørn sad på kode-fladen, og
 * varslet blev aldrig hentet — i 11½ time, uden en eneste fejl noget sted.
 * Fire rettelser gik til en komponent der ikke var på skærmen.
 *
 * Mobilen gør det rigtige i dag: begge skærme er monteret, og den inaktive
 * gemmes med et style-flag. Men det står kun som en kommentar, og en
 * kommentar holder ikke noget fast. Denne test gør det.
 *
 * AST, ikke grep: navnet står også i import-linjen, og en grep ville bestå
 * selv om elementet blev flyttet ind bag `mode === 'snak' &&`. Den fejl har
 * jeg lavet før — se `source_guards_need_ast`.
 */
const KILDE = resolve(__dirname, '../App.tsx')
const SKAERM = 'ChatScreen'

/** Den nærmeste betingelse der ville kunne unmounte elementet. */
function fladeBetingelseOmkring(node: ts.Node): string | null {
  for (let n: ts.Node | undefined = node.parent; n; n = n.parent) {
    if (ts.isBinaryExpression(n)
        && n.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken) {
      return n.left.getText()
    }
    if (ts.isConditionalExpression(n)) return n.condition.getText()
  }
  return null
}

describe('App holder chat-skærmen monteret', () => {
  const kilde = ts.createSourceFile(
    KILDE, readFileSync(KILDE, 'utf-8'), ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)

  const brug: ts.Node[] = []
  const gaa = (n: ts.Node) => {
    if ((ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n))
        && n.tagName.getText() === SKAERM) brug.push(n)
    ts.forEachChild(n, gaa)
  }
  gaa(kilde)

  it('bruges som element præcis ét sted', () => {
    expect(brug).toHaveLength(1)
  })

  it('står ikke bag en flade-betingelse — så ville effekten ikke køre', () => {
    const betingelse = fladeBetingelseOmkring(brug[0]!)
    expect(betingelse).toBeNull()
  })
})
