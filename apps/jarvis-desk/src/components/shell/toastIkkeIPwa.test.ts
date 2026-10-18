import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ts from 'typescript'

/**
 * Notifikations-toasten maa ikke monteres i PWA-bygget.
 *
 * Bjørn 18/10-2026: «notifikations toast skal ikk vises i pwa mode». PWA'en
 * har sin egen kanal — web-push til operativsystemet — og den naar ogsaa frem
 * naar fanen er lukket, hvilket en toast i DOM'en ikke kan. Begge kanaler paa
 * én gang betyder at man faar beskeden to gange.
 *
 * AST, ikke grep: navnet staar ogsaa i import-linjen, saa en grep ville
 * bestaa selv om kontakten blev fjernet igen. Det er den fejl
 * `source_guards_need_ast` advarer om, og den er lavet foer.
 */
const KILDE = resolve(__dirname, '../../App.tsx')
const TOAST = 'NotifikationsToast'

/** Er elementet gatet paa `__WEB_BUILD__` — og i hvilken retning? */
function pwaGateOmkring(node: ts.Node): string | null {
  for (let n: ts.Node | undefined = node.parent; n; n = n.parent) {
    if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken) {
      const v = n.left.getText()
      if (v.includes('__WEB_BUILD__')) return v
    }
    if (ts.isConditionalExpression(n) && n.condition.getText().includes('__WEB_BUILD__')) {
      return n.condition.getText()
    }
  }
  return null
}

function findToastElementer(): ts.Node[] {
  const tekst = readFileSync(KILDE, 'utf8')
  const sf = ts.createSourceFile(KILDE, tekst, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  const fundet: ts.Node[] = []
  const gaa = (node: ts.Node) => {
    // Selv-lukkende OG med børn: toasten er selv-lukkende i dag, men en vagt
    // der kun kender den ene form bestaar tavst hvis formen skifter.
    if (ts.isJsxSelfClosingElement(node) && node.tagName.getText() === TOAST) {
      fundet.push(node)
    } else if (ts.isJsxElement(node) && node.openingElement.tagName.getText() === TOAST) {
      fundet.push(node)
    }
    ts.forEachChild(node, gaa)
  }
  gaa(sf)
  return fundet
}

describe('notifikations-toasten i PWA', () => {
  it('monteres kun naar bygget IKKE er PWA', () => {
    const elementer = findToastElementer()
    expect(elementer.length, `${TOAST} skal monteres praecis ét sted i App.tsx`).toBe(1)

    const foerste = elementer[0]
    expect(foerste, `${TOAST} blev ikke fundet i App.tsx`).toBeTruthy()
    const gate = pwaGateOmkring(foerste!)
    expect(gate, `${TOAST} staar uden en __WEB_BUILD__-kontakt — den vises saa ogsaa i PWA'en`).toBeTruthy()

    // Retningen er pointen: `!__WEB_BUILD__` = kun desk. Uden `!` ville den
    // vaere monteret KUN i PWA'en — praecis det modsatte af hvad der blev bedt om.
    expect(gate, 'kontakten skal vaere !__WEB_BUILD__ (kun desk), ikke det modsatte').toMatch(/^!\s*__WEB_BUILD__$/)
  })
})
