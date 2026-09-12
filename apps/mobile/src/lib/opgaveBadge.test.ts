import { erAfbrudt, erAutonom, taelOpgaverDerKalder } from './opgaveBadge'
import type { McRun } from './mcTypes'

const run = (o: Partial<McRun>): McRun => ({
  run_id: 'r', lane: 'primary', provider: null, model: null,
  status: 'completed', started_at: '', finished_at: null, text_preview: null, ...o,
})

// Maalt paa runtime 12/9-2026 over 18.202 runs: primary 17.866, agent 301,
// local 19, visible 2. Bjoerns egne ture ligger under `primary` — ikke under
// `visible`, som navnet lover og som har to raekker i alt.

describe('erAutonom', () => {
  it('primary og visible er HANS egne', () => {
    expect(erAutonom(run({ lane: 'primary' }))).toBe(false)
    expect(erAutonom(run({ lane: 'visible' }))).toBe(false)
  })
  it('agent og local koerte uden at han bad om det', () => {
    expect(erAutonom(run({ lane: 'agent' }))).toBe(true)
    expect(erAutonom(run({ lane: 'local' }))).toBe(true)
  })
  it('ukendt bane regnes som autonom — det sikre gaet er at vise den', () => {
    expect(erAutonom(run({ lane: 'noget-nyt' }))).toBe(true)
  })
})

describe('erAfbrudt', () => {
  it('interrupted og failed taeller', () => {
    expect(erAfbrudt(run({ status: 'interrupted' }))).toBe(true)
    expect(erAfbrudt(run({ status: 'failed' }))).toBe(true)
  })
  it('completed goer ikke', () => {
    expect(erAfbrudt(run({ status: 'completed' }))).toBe(false)
  })
  it('cancelled goer HELLER ikke — man afbroed selv', () => {
    // En prik for noget man selv har standset er stoej.
    expect(erAfbrudt(run({ status: 'cancelled' }))).toBe(false)
  })
})

describe('taelOpgaverDerKalder', () => {
  it('en almindelig faerdig tur af hans egen giver ingen prik', () => {
    // Kontrolarm. Uden den ville en taeller der altid gav >0 bestaa nedenfor.
    expect(taelOpgaverDerKalder([run({})])).toBe(0)
  })
  it('en autonom tur taeller', () => {
    expect(taelOpgaverDerKalder([run({ lane: 'agent' })])).toBe(1)
  })
  it('en afbrudt tur af hans egen taeller ogsaa', () => {
    expect(taelOpgaverDerKalder([run({ status: 'interrupted' })])).toBe(1)
  })
  it('en tur der er BEGGE dele taelles én gang', () => {
    expect(taelOpgaverDerKalder([run({ lane: 'agent', status: 'failed' })])).toBe(1)
  })
  it('tom eller manglende liste giver nul', () => {
    expect(taelOpgaverDerKalder([])).toBe(0)
    expect(taelOpgaverDerKalder(null)).toBe(0)
  })
})

it('WorkScreen KALDER taelleren paa Tasks-fanen', () => {
  // Koblingen. Taelleren kan vaere rigtig og fanen stadig uden prik —
  // det er den fejl hele filen findes for. En ren funktion ingen kalder
  // viser ingenting.
  const kilde = require('fs').readFileSync(
    require('path').join(__dirname, '..', 'screens', 'WorkScreen.tsx'), 'utf8') as string
  const tasksLinje = kilde.split('\n').find((l) => l.includes("value: 'tasks'")) ?? ''
  expect(tasksLinje).toContain('badge:')
  expect(tasksLinje).toContain('taelOpgaverDerKalder')
})
