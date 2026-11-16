import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import ts from 'typescript'
import { findesGodkendelseIRækken, afstemVentendeGodkendelse } from './ventendeGodkendelse'

/** Godkendelsen maa ikke kunne forsvinde — og den maa ikke staa to steder.
 *
 *  MAALT 31/10-2026: efter 0.6.294 saa Bjoern INTET kort i PWA'en. DEL 3
 *  havde flyttet kortet ind i transcriptet og fjernet det flydende — men den
 *  persisterede raekke kom aldrig, saa spoergsmaalet fandtes ikke paa skaermen.
 *
 *  16/11-2026 — VENDT TILBAGE, og aarsagen er den modsatte fejl. DEL 3 gjorde
 *  raekken til den PRIMAERE flade og det flydende kort til en fallback bag
 *  `!pendingIRækken`. Bjoern: «approval cards lander over turhoved og ikk over
 *  composer som de skulle??? hver gang der kommer en skal jeg scrolle til
 *  toppen af din tur for at godkende!»
 *
 *  Spoergsmaalet stod altsaa oeverst i turen og skulle FINDES, ikke bare
 *  besvares. Kontrakten er nu: `.composer-notices` er ALTID fladen (den ligger
 *  uden for scroll-containeren), og raekken i transcriptet er ren historik uden
 *  knapper. Der er praecis ÉN flade at svare paa.
 *
 *  En kommentar er ikke en vagt — derfor maaler testen kilden.
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

  it('svarer nej naar rækken ikke er kommet endnu', () => {
    expect(findesGodkendelseIRækken([], 'a1')).toBe(false)
    expect(findesGodkendelseIRækken([{ role: 'user', content_json: null }], 'a1')).toBe(false)
  })

  it('matcher ALDRIG paa tekst: to godkendelser med samme kommando', () => {
    // Samme kommando, forskelligt id. Et tekst-match ville pege paa den
    // forkerte raekke — og et svar paa det forkerte spoergsmaal.
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

describe('kortet over composeren er den ENESTE flade der kan besvares', () => {
  // 16/11-2026. Den gamle kontrakt hed «raekken vinder naar den findes» og blev
  // maalt med `findesSynligGodkendelseRaekke`. Den funktion er slettet sammen
  // med sin gate: spoergsmaalet skal staa fast over composeren, ikke findes.
  //
  // Den maaling der stadig er vaerd at huske (12/11, godkendelse 272681): en
  // afventende raekke blev flettet ind i en heartbeat-besked og forsvandt som
  // fri raekke — spoergsmaalet var hverken raekke eller kort i ca. 3 minutter.
  // Netop derfor maa kortet ikke afhaenge af raekken overhovedet.
  for (const view of ['ChatView.tsx', 'CodeView.tsx']) {
    it(`${view} gater IKKE kortet paa om raekken findes`, () => {
      const kilde = readFileSync(resolve(SRC, 'views', view), 'utf-8')
      expect(kilde, 'gaten `!pendingIRækken` er tilbage — saa forsvinder kortet '
        + 'fra composeren praecis naar det skal staa der').not.toContain('pendingIRækken')
      expect(kilde).toContain('GodkendelsesKort')
    })

    it(`${view} giver IKKE raekken knapper`, () => {
      const kilde = readFileSync(resolve(SRC, 'views', view), 'utf-8')
      expect(kilde, 'raekken fik knapper igen — saa er der to steder at svare, '
        + 'og det ene skal man scrolle til').not.toContain('liveGodkendelse')
    })

    it(`${view} tegner kortet praecis ét sted`, () => {
      const kilde = readFileSync(resolve(SRC, 'views', view), 'utf-8')
      const antal = kilde.split('<GodkendelsesKort').length - 1
      expect(antal).toBe(1)
    })
  }
})

describe('afstemning af kortet klienten HOLDER mod hvad serveren siger venter', () => {
  // MÅLT 12/11-2026 (CT105, 15:45–15:57): 19 godkendelser, og ALLE blev afgjort
  // via notifikations-feedet (/notifikationer/<id>/afgoer) — ingen via
  // composer-kortet. Effekten holdt op med at polle så snart den HAVDE et kort,
  // og kortet ryddes kun af message_stop, nyt send, eget klik eller udløb
  // (3600 s). Et kort afgjort et andet sted blev derfor stående — og blokerede
  // opsamlingen af alle de næste.
  const a1 = { approvalId: 'a1', kind: 'tool' as const }
  const a2 = { approvalId: 'a2', kind: 'tool' as const }

  it('intet kort holdt, intet fundet → behold', () => {
    expect(afstemVentendeGodkendelse(null, null, 0)).toEqual({ handling: 'behold', tommeISnor: 0 })
  })

  it('intet kort holdt, et fundet → skift til det', () => {
    expect(afstemVentendeGodkendelse(null, a1, 0)).toEqual({ handling: 'skift', tommeISnor: 0 })
  })

  it('samme kort stadig ventende → behold og nulstil tælleren', () => {
    expect(afstemVentendeGodkendelse(a1, a1, 1)).toEqual({ handling: 'behold', tommeISnor: 0 })
  })

  it('serveren venter på et ANDET kort → skift (det holdte er afgjort et andet sted)', () => {
    expect(afstemVentendeGodkendelse(a1, a2, 0)).toEqual({ handling: 'skift', tommeISnor: 0 })
  })

  it('ét tomt svar rydder IKKE — en enkelt netværksfejl er også «intet»', () => {
    expect(afstemVentendeGodkendelse(a1, null, 0)).toEqual({ handling: 'behold', tommeISnor: 1 })
  })

  it('to tomme svar i træk rydder kortet — det er afgjort', () => {
    expect(afstemVentendeGodkendelse(a1, null, 1)).toEqual({ handling: 'ryd', tommeISnor: 0 })
  })

  it('et AGENT-kort røres ikke af tool-opsamlingen', () => {
    const agent = { approvalId: 'g1', kind: 'agent' as const }
    expect(afstemVentendeGodkendelse(agent, null, 5)).toEqual({ handling: 'behold', tommeISnor: 0 })
    expect(afstemVentendeGodkendelse(agent, a1, 0)).toEqual({ handling: 'behold', tommeISnor: 0 })
  })

  it('et kort uden kind er et tool-kort (alt der kom før feltet fandtes)', () => {
    expect(afstemVentendeGodkendelse({ approvalId: 'a1' }, null, 1)).toEqual({ handling: 'ryd', tommeISnor: 0 })
  })
})

describe('StreamContext afstemmer det holdte kort mod serveren', () => {
  it('opsamlingen kalder afstemVentendeGodkendelse', () => {
    const fil = resolve(SRC, 'contexts', 'StreamContext.tsx')
    const kilde = ts.createSourceFile(fil, readFileSync(fil, 'utf-8'),
      ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX)
    let kald = 0
    const gaa = (n: ts.Node) => {
      if (ts.isCallExpression(n) && n.expression.getText() === 'afstemVentendeGodkendelse') kald += 1
      ts.forEachChild(n, gaa)
    }
    gaa(kilde)
    expect(kald, 'uden afstemningen bliver et kort afgjort et andet sted staaende '
      + 'og blokerer opsamlingen af de naeste (maalt 12/11-2026)').toBeGreaterThan(0)
  })
})
