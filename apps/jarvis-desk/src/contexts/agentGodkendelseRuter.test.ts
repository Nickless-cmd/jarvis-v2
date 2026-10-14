import { describe, it, expect } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

/**
 * To slags godkendelser, to ruter — og kortet skal kunne svare på BEGGE.
 *
 * Bjørn 14/10-2026: «nu dukker de kun op i notifikations feed og forlanger totp
 * for godkendelse». Det var ikke én fejl men to: en agent-godkendelse nåede
 * aldrig kortet over composeren, og den vej der fandtes krævede en kode.
 *
 * Kilden læses frem for at rende hele StreamContext op: det der skal pinnes er
 * ikke hvordan tilstanden tegnes, men at BEGGE spørgsmål stilles og at svaret
 * går ad den rigtige rute. Fjerner nogen agent-grenen, er posten usynlig igen —
 * og det er præcis den regression denne fil fanger.
 *
 * Samme mønster som `godkendelseskortetTegnesEtSted.test.ts`: et navn i en
 * import-linje er ikke et kald.
 */
const SRC = resolve(__dirname, '..')
const stream = readFileSync(resolve(SRC, 'contexts/StreamContext.tsx'), 'utf-8')

describe('agent-godkendelser i StreamContext', () => {
  it('spørger OGSÅ agent-vejen når tool-vejen svarer intet', () => {
    expect(stream).toContain('hentVentendeAgentGodkendelse')
    // Kaldet, ikke bare navnet: `hentVentendeAgentGodkendelse(cfg)` er formen.
    expect(stream).toContain('hentVentendeAgentGodkendelse(cfg)')
  })

  it('afgør et agent-kort ad agent-ruten — ikke tool-ruten', () => {
    expect(stream).toContain('afgoerAgentApproval(config, approvalId, decision')
    // Forgreningen er på `kind`, og den skal stå FØR tool-kaldet: ellers ville
    // et agent-kort blive sendt til en rute der ikke kender posten.
    const iAgent = stream.indexOf('afgoerAgentApproval(config, approvalId, decision')
    const iTool = stream.indexOf('approveTool(config, approvalId)')
    expect(iAgent).toBeGreaterThan(-1)
    expect(iTool).toBeGreaterThan(-1)
    expect(iAgent).toBeLessThan(iTool)
  })

  it('bærer agent-kortets digest og session med i afgørelsen', () => {
    expect(stream).toContain('post.digest')
    expect(stream).toContain('post.sessionId')
  })

  it('kender kun to slags — og fraværende kind betyder tool', () => {
    expect(stream).toContain("kind?: 'tool' | 'agent'")
    // Den gamle vej skal stadig stemples eksplicit, saa en post fra foer feltet
    // fandtes ikke pludselig gaar ad en ny rute.
    expect(stream).toContain("kind: 'tool'")
    expect(stream).toContain("kind: 'agent'")
  })
})
