import { describe, expect, it } from 'vitest'
import { svarPacingGate, type PacingInput } from './svarPacing'
import { udenAktivRun } from './transcriptFilter'

const SVAR =
  'Det endelige svar står her og er langt nok til at tælle som et rigtigt svar. ' +
  'Det fortsætter over flere linjer, præcis som svarene i den virkelige flade.'

const grund = (over: Partial<PacingInput> = {}): PacingInput => ({
  status: 'done',
  activeRunId: 'visible-x',
  pacedAnswerRunId: null,
  harSlutblok: true,
  finalAnswerStarted: true,
  levendeTekst: SVAR,
  ...over,
})

describe('svarPacingGate', () => {
  // ── Det målte tilfælde (Bjørn 29/10-2026) ──────────────────────────────
  //
  // Turen går tilbage til værktøjsarbejde EFTER teksten. `deriveChatFlow`
  // flytter blokken ud af `finalBlocks` (den sidste grænse ligger nu efter
  // teksten), så `harSlutblok` bliver falsk — men teksten ER på skærmen og
  // pacen er i gang. Faldt filteret bort her, blev serverens persisterede
  // række tegnet oven over den halvt-pacede tekst.
  it('holder filteret aktivt naar finalBlocks tommes midt i pace-vinduet', () => {
    const gate = svarPacingGate(grund({ harSlutblok: false }))
    expect(gate.paceVindue).toBe(true)
    expect(gate.visLevendeTur).toBe(true)
    expect(gate.filterAktiv).toBe(true)
  })

  it('skjuler den persisterede raekke gennem hele vinduet — ikke kun foerste frame', () => {
    const raekker = [
      { id: 'u1', role: 'user' },
      { id: 'a-visible-x', role: 'assistant', content: [{ type: 'text', text: SVAR }] },
      { id: 'message-1', role: 'assistant', run_id: 'visible-x', content: [{ type: 'text', text: SVAR }] },
    ]
    const gate = svarPacingGate(grund({ harSlutblok: false }))
    const ud = udenAktivRun(raekker, 'visible-x', gate.filterAktiv, SVAR)
    expect(ud.map((m) => m.id)).toEqual(['u1'])
  })

  // ── Modsatte side: en TOM levende tur maa ikke skjule noget ─────────────
  //
  // Det er den farlige retning. Skjuler filteret den persisterede række mens
  // den levende tur er tom, er der intet svar tilbage paa skaermen.
  it('skjuler intet naar den levende tur ikke har indhold', () => {
    // Scenariet skal vaere et hvor turen FAKTISK tegnes — ellers er der intet
    // at skjule, og testen faelder ikke mutationen. Maalt 29/10-2026: foerste
    // udgave brugte status='done', hvor visLevendeTur ogsaa er falsk, saa
    // modproeven gik igennem med 7 passed.
    const gate = svarPacingGate(grund({ status: 'working', levendeTekst: '' }))
    expect(gate.visLevendeTur).toBe(true) // turen tegnes ...
    expect(gate.filterAktiv).toBe(false) // ... men der er intet at skjule bag den
  })

  // ── Den normale vej: finalBlocks har teksten ────────────────────────────
  it('lader paceren koere naar finalBlocks baerer slutteksten', () => {
    const gate = svarPacingGate(grund())
    expect(gate.afslutterSvarPacing).toBe(true)
    expect(gate.filterAktiv).toBe(true)
  })

  it('er faerdig naar runnet allerede er markeret pacet', () => {
    const gate = svarPacingGate(grund({ pacedAnswerRunId: 'visible-x' }))
    expect(gate.paceVindue).toBe(false)
    expect(gate.afslutterSvarPacing).toBe(false)
    expect(gate.filterAktiv).toBe(false)
  })

  it('tegner den levende tur mens stroemmen loeber', () => {
    const gate = svarPacingGate(grund({ status: 'working', harSlutblok: false }))
    expect(gate.paceVindue).toBe(false)
    expect(gate.visLevendeTur).toBe(true)
    expect(gate.filterAktiv).toBe(true)
  })

  it('er helt passiv uden et aktivt run', () => {
    const gate = svarPacingGate(grund({ activeRunId: null }))
    expect(gate.paceVindue).toBe(false)
    expect(gate.visLevendeTur).toBe(false)
    expect(gate.filterAktiv).toBe(false)
  })
})
