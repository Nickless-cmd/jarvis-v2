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
    //
    // 31/10-2026 — DEL 3: kortet flyttede fra `.composer-area` IND i
    // transcriptet, saa det ikke skubber samtalen op. Kontrakten er den samme,
    // men fladen der baerer den er nu `HistoriskGodkendelse` i
    // `approval_request`-grenen. Testen maaler derfor den gren, ikke det
    // flydende kort — ellers ville den kraeve den komponent vi netop fjernede.
    const mangler = tsxFiler(VIEWS)
      .filter((f) => jsxNavne(f).includes('Composer'))
      .filter((f) => !jsxNavne(f).includes('HistoriskGodkendelse'))
      .map((f) => f.slice(VIEWS.length + 1))
    expect(mangler, 'en flade kan sende, men kan ikke svare paa en godkendelse '
      + '— saa ser den ud som om Jarvis er staaet af').toEqual([])
  })

  it('hver flade med en composer har BAADE historik og et besvarbart kort', () => {
    // 16/11-2026 — KONTRAKTEN BLEV VENDT AF EN MAALING IGEN.
    //
    // 31/10 (DEL 3) gjorde raekken i transcriptet til den primaere flade og
    // dette kort til en fallback bag `!pendingIRækken`. Bjoern: «approval cards
    // lander over turhoved og ikk over composer som de skulle??? hver gang der
    // kommer en skal jeg scrolle til toppen af din tur for at godkende!»
    //
    // Spoergsmaalet stod oeverst i turen og skulle FINDES. Nu er
    // `.composer-notices` altid fladen — den ligger uden for scroll-containeren
    // — og raekken er ren historik. Begge skal vaere der: historikken for at
    // svaret kan findes igen, kortet for at spoergsmaalet kan besvares.
    //
    // At gaten ikke maa vaere der, og at raekken ikke maa have knapper, maales i
    // `lib/ventendeGodkendelse.test.ts` — her maales kun at begge flader findes.
    const mangler = tsxFiler(VIEWS)
      .filter((f) => jsxNavne(f).includes('Composer'))
      .filter((f) => {
        const navne = jsxNavne(f)
        return !navne.includes('HistoriskGodkendelse') || !navne.includes('GodkendelsesKort')
      })
      .map((f) => f.slice(VIEWS.length + 1))
    expect(mangler, 'en flade kan sende, men kan ikke baade svare paa en '
      + 'godkendelse og finde svaret igen').toEqual([])
  })
})
