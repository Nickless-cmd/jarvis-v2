import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ts from 'typescript'
import { findesGodkendelseIRækken, findesSynligGodkendelseRaekke } from './ventendeGodkendelse'

/** Godkendelsen maa ikke kunne forsvinde — og den maa ikke staa to steder.
 *
 *  MAALT 31/10-2026: efter 0.6.294 saa Bjoern INTET kort i PWA'en. DEL 3
 *  havde flyttet kortet ind i transcriptet og fjernet det flydende — men den
 *  persisterede raekke kom aldrig, saa spoergsmaalet fandtes ikke paa skaermen.
 *  Han maatte ind i APK'en (gamle bundle) for at godkende.
 *
 *  Kontrakten er derfor: ÉN betingelse, to flader. Raekken vinder naar den
 *  findes; ellers bærer det flydende kort svaret. Testen maaler baade
 *  funktionen og at viewene faktisk bruger dens negation som gate — en
 *  kommentar er ikke en vagt.
 */

const SRC = resolve(__dirname, '..')

function kort(approval_id: string, status = 'pending') {
  return {
    role: 'approval_request',
    content_json: [{ approval_id, tool: 'exec_command', action: 'rm -rf /tmp/x', status }],
  }
}

describe('findesGodkendelseIRækken', () => {
  it('finder rækken paa approval_id', () => {
    expect(findesGodkendelseIRækken([kort('a1')], 'a1')).toBe(true)
  })

  it('svarer nej naar rækken ikke er kommet endnu — saa vises fallbacken', () => {
    expect(findesGodkendelseIRækken([], 'a1')).toBe(false)
    expect(findesGodkendelseIRækken([{ role: 'user', content_json: null }], 'a1')).toBe(false)
  })

  it('matcher ALDRIG paa tekst: to godkendelser med samme kommando', () => {
    // Samme kommando, forskelligt id. Et tekst-match ville give knapper paa
    // den forkerte raekke — og et svar paa det forkerte spoergsmaal.
    expect(findesGodkendelseIRækken([kort('a2')], 'a1')).toBe(false)
  })

  it('en afgjort raekke taeller stadig som "findes" — svaret er givet', () => {
    expect(findesGodkendelseIRækken([kort('a1', 'approved')], 'a1')).toBe(true)
  })

  it('taaler en raekke uden content_json uden at kaste', () => {
    expect(findesGodkendelseIRækken([{ role: 'approval_request' }], 'a1')).toBe(false)
    expect(findesGodkendelseIRækken([{ role: 'approval_request', content_json: 'noget' }], 'a1')).toBe(false)
  })

  it('svarer nej uden ventende godkendelse', () => {
    expect(findesGodkendelseIRækken([kort('a1')], null)).toBe(false)
  })
})

/** AST, ikke grep: navnet staar ogsaa i import-linjen. */
function fallbackGate(view: string): string {
  const fil = resolve(SRC, 'views', view)
  const kilde = ts.createSourceFile(fil, readFileSync(fil, 'utf-8'),
    ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
  let fundet: ts.Node | undefined
  const gaa = (n: ts.Node) => {
    if ((ts.isJsxSelfClosingElement(n) || ts.isJsxOpeningElement(n))
      && n.tagName.getText() === 'GodkendelsesKort') fundet = n
    ts.forEachChild(n, gaa)
  }
  gaa(kilde)
  if (!fundet) return ''
  // Gaa op til den naermeste betingelse og laes HELE dens udtryk.
  let n: ts.Node | undefined = fundet
  while (n) {
    if (ts.isConditionalExpression(n) || ts.isBinaryExpression(n) || ts.isJsxExpression(n)) {
      const tekst = n.getText()
      if (tekst.includes('pendingIRækken')) return tekst
    }
    n = n.parent
  }
  return ''
}

describe('fallback-kortet er betinget, ikke dubleret', () => {
  for (const view of ['ChatView.tsx', 'CodeView.tsx']) {
    it(`${view} viser kun det flydende kort naar raekken MANGLER`, () => {
      const gate = fallbackGate(view)
      expect(gate, 'det flydende kort blev fjernet uden en fallback — saa '
        + 'forsvinder spoergsmaalet indtil raekken lander (maalt 31/10)').not.toBe('')
      expect(gate).toContain('!pendingIRækken')
      expect(gate).toContain('pendingApproval')
    })
  }
})

describe('en afventende godkendelse der er flettet ind i en andens besked', () => {
  // MÅLT 12/11-2026 på CT105 (chat_messages, session chat-ed2df…): en
  // heartbeat-besked (id 272703) landede 15:53:03 MIDT i et run, mens
  // godkendelsen 272681 stadig ventede (afgjort 15:54:11). `fletGodkendelser`
  // lagde den afventende række ind i den besked — uden knapper, i en fold — og
  // fjernede den som fri række. Men `findesGodkendelseIRækken` læste de RÅ
  // beskeder og svarede «rækken findes», så composer-kortet blev skjult.
  // Resultat: hverken række eller kort i ca. 3 minutter.
  const pending = {
    id: 'm1', role: 'approval_request', content: 'Godkendelse afventer: bash — ls',
    content_json: [{ approval_id: 'a1', tool: 'bash', action: 'ls', status: 'pending' }],
    created_at: '2026-11-12T15:51:16+00:00', parent_id: null,
  }
  const hjerteslag = {
    id: 'm2', role: 'assistant',
    content: [{ type: 'text', text: '🌙 Hjerteslag — hvad jeg lavede mens du var væk' }],
    created_at: '2026-11-12T15:53:03+00:00', parent_id: null,
  }

  it('tæller IKKE som en synlig række — composer-kortet skal bære den', () => {
    expect(findesSynligGodkendelseRaekke([pending, hjerteslag] as never, 'a1')).toBe(false)
  })

  it('tæller som en række når intet følger efter — rækken har selv knapperne', () => {
    expect(findesSynligGodkendelseRaekke([pending] as never, 'a1')).toBe(true)
  })

  it('en tom id giver false uden at flette', () => {
    expect(findesSynligGodkendelseRaekke([pending] as never, null)).toBe(false)
  })
})

describe('viewene spørger den FLETTEDE liste, ikke de rå beskeder', () => {
  for (const view of ['ChatView.tsx', 'CodeView.tsx']) {
    it(`${view} beregner pendingIRækken med findesSynligGodkendelseRaekke`, () => {
      const fil = resolve(SRC, 'views', view)
      const kilde = ts.createSourceFile(fil, readFileSync(fil, 'utf-8'),
        ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
      let init = ''
      const gaa = (n: ts.Node) => {
        if (ts.isVariableDeclaration(n) && n.name.getText() === 'pendingIRækken') {
          init = n.initializer?.getText() ?? ''
        }
        ts.forEachChild(n, gaa)
      }
      gaa(kilde)
      expect(init, 'pendingIRækken blev ikke fundet').not.toBe('')
      expect(init).toContain('findesSynligGodkendelseRaekke(')
    })
  }
})
