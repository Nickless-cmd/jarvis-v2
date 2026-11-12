/**
 * Opdagelsen af et nyt run må ikke bremses af hvile-tilstanden (12/11-2026).
 *
 * Målt: wake-runnet autonomous-7d13b933 startede 19:11:20 og varede 20 s; desk
 * tilsluttede sig 19:11:37. Pollen af /chat/active-runs kom 19:11:13 og så :11:37 (24 s)
 * fordi hvile-faktoren 8 ramte både pollen og den delte cache. `loftSynligMs` er
 * rettelsen — og den virker kun hvis de tre steder faktisk sender den med.
 */
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { describe, expect, it } from 'vitest'
import ts from 'typescript'

const SRC = resolve(__dirname, '..')

function kilde(rel: string): ts.SourceFile {
  const fil = resolve(SRC, rel)
  return ts.createSourceFile(fil, readFileSync(fil, 'utf-8'), ts.ScriptTarget.Latest, true,
    fil.endsWith('x') ? ts.ScriptKind.TSX : ts.ScriptKind.TS)
}

/** Første kald til `navn` hvis første argument er strengen `noegle`. */
function kaldMedNoegle(sf: ts.SourceFile, navn: string, noegle: string): ts.CallExpression | undefined {
  let fundet: ts.CallExpression | undefined
  const gaa = (n: ts.Node) => {
    if (ts.isCallExpression(n) && n.expression.getText() === navn) {
      const a0 = n.arguments[0]
      if (a0 && (ts.isStringLiteral(a0) || ts.isNoSubstitutionTemplateLiteral(a0)) && a0.text === noegle) fundet = n
      if (a0 && ts.isTemplateExpression(a0) && a0.getText().includes(noegle)) fundet = n
    }
    ts.forEachChild(n, gaa)
  }
  gaa(sf)
  return fundet
}

describe('loftSynligMs er koblet på alle steder der opdager et nyt run', () => {
  for (const [fil, noegle] of [['views/ChatView.tsx', 'chat-aktive-runs'], ['views/CodeView.tsx', 'kode-aktive-runs']] as const) {
    it(`${fil} sender loftSynligMs med til maaPolle('${noegle}')`, () => {
      const kald = kaldMedNoegle(kilde(fil), 'maaPolle', noegle)
      expect(kald, `maaPolle('${noegle}') findes ikke længere`).toBeDefined()
      expect(kald!.arguments[2]?.getText() ?? '', 'loftSynligMs mangler — et synligt vindue i ro '
        + 'opdager igen vækninger 12-28 s for sent').toContain('loftSynligMs')
    })
  }

  it('den delte læsning getActiveRunSessions sender loftSynligMs til sharedRead', () => {
    const kald = kaldMedNoegle(kilde('lib/api.ts'), 'sharedRead', 'active-runs:')
    expect(kald, 'sharedRead(active-runs) findes ikke længere').toBeDefined()
    expect(kald!.arguments[2]?.getText() ?? '').toContain('loftSynligMs')
  })
})
