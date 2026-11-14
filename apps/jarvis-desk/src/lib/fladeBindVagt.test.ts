/**
 * Kilde-vagter for fladernes bind-logik.
 *
 * ## Hvorfor de læser KILDEN og ikke opfører sig
 * To fejl i denne fil-familie kan en adfærdstest ikke se:
 *
 * 1. **`e.currentTarget` inde i et state-kald.** React nulstiller
 *    `currentTarget` når handleren returnerer. Læses den inde i
 *    opdateringsfunktionen — som kører under render, bagefter — er den `null`,
 *    og hele beskeden kaster «Cannot read properties of null». Målt 14/11-2026:
 *    mutationsprøven BESTOD med den brækkede kode, fordi jsdom ikke nulstiller
 *    `currentTarget` som en rigtig browser gør. Testen kunne altså ikke se
 *    fejlen den var skrevet til at fange.
 *
 * 2. **Tilbagefald til ren regex-interpolation.** `{seats*29}` blev stående
 *    som tekst før 14/11-2026. Ruller nogen interpolationen tilbage til
 *    `/\{(\w+)\}/`, forsvinder udtrykkene uden at nogen test siger fra — den
 *    gamle adfærd var jo «korrekt» for rene bind-navne.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ts from 'typescript'
import { describe, expect, it } from 'vitest'

const FILER = [
  resolve(__dirname, '../components/rich/NativeRichBlock.tsx'),
  resolve(__dirname, '../../../mobile/src/components/NativeRichBlock.tsx'),
]

/** Gå gennem alle noder i et parsét træ. */
function gaa(node: ts.Node, fn: (n: ts.Node) => void): void {
  fn(node)
  node.forEachChild((barn) => gaa(barn, fn))
}

describe('fladernes bind-logik — kilde-vagter', () => {
  it.each(FILER)('%s: læser ikke e.currentTarget inde i et state-kald', (fil) => {
    const kilde = readFileSync(fil, 'utf8')
    const sf = ts.createSourceFile(fil, kilde, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    const synder: string[] = []
    gaa(sf, (n) => {
      if (!ts.isCallExpression(n)) return
      const navn = n.expression.getText(sf)
      if (navn !== 'setKontrolVaerdi') return
      // Alt inde i argumenterne: både `e.currentTarget` og `e.target` er
      // farlige her, fordi begge læses efter handleren er returneret.
      for (const arg of n.arguments) {
        gaa(arg, (indre) => {
          if (!ts.isPropertyAccessExpression(indre)) return
          const prop = indre.name.text
          if (prop === 'currentTarget' || prop === 'target') {
            const linje = sf.getLineAndCharacterOfPosition(indre.getStart(sf)).line + 1
            synder.push(`linje ${linje}: ${indre.getText(sf)}`)
          }
        })
      }
    })
    expect(synder, `Værdien skal ud af eventet FØR state-kaldet:\n${synder.join('\n')}`).toEqual([])
  })

  it.each(FILER)('%s: interpolerer gennem den lukkede evaluator', (fil) => {
    const kilde = readFileSync(fil, 'utf8')
    expect(kilde).toContain('interpolérUdtryk')
    // Den gamle, rene regex-interpolation. Står den her, er udtryk som
    // `{seats*29}` stille holdt op med at virke.
    expect(kilde, 'ren regex-interpolation er rullet tilbage').not.toContain('(\\w+)')
  })

  it('desk og mobil deler samme evaluator — ikke to kopier der driver fra hinanden', () => {
    const desk = readFileSync(resolve(__dirname, 'udtryk.ts'), 'utf8')
    const mobil = readFileSync(resolve(__dirname, '../../../mobile/src/lib/udtryk.ts'), 'utf8')
    // Kopien er bevidst (de to apps har hver sin bundling), men en kopi der
    // er drevet fra hinanden er værre end ingen kopi: så retter man fejlen i
    // den ene og tror den er væk.
    expect(mobil).toBe(desk)
  })
})
