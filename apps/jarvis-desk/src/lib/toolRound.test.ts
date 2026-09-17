import { describe, it, expect } from 'vitest'
import { describeTool, summarizeRound, countFromResult, subjectFromInput } from './toolRound'
import type { ContentBlock } from './sseProtocol'

type ToolUse = Extract<ContentBlock, { type: 'tool_use' }>
const t = (name: string, input: Record<string, unknown>, status: 'done' | 'running' = 'done', result?: string): ToolUse =>
  ({ type: 'tool_use', id: name + JSON.stringify(input), name, input, status, result })

/**
 * Porteret 1:1 fra mobilens toolSummary.ts + toolGroup.ts (Bjørn 8/9-2026:
 * «det skal lige 1:1 — det er i den mobil app du byggede på tidligere»).
 */

describe('linjen siger hvad der laves, ikke hvilket værktøj', () => {
  it('bruger emnet frem for værktøjsnavnet', () => {
    expect(describeTool('read_file', { path: '/a/b/agent.ts' }, false)).toBe('Læste agent.ts')
  })

  it('bøjer verbet mens det kører', () => {
    expect(describeTool('read_file', { path: 'x.ts' }, true)).toBe('Læser x.ts…')
  })

  it('falder tilbage på værktøjsnavnet frem for at finde på noget', () => {
    expect(describeTool('mystisk_ting', {}, false)).toBe('Kørte mystisk_ting')
  })

  it('operator-varianten er samme handling for læseren', () => {
    // `operator_read_file` og `read_file` gør det samme; kun navnet er andet.
    expect(describeTool('operator_read_file', { path: 'x.ts' }, false)).toBe('Læste x.ts')
  })

  it('en sti bliver til filnavnet', () => {
    expect(subjectFromInput({ path: '/meget/lang/sti/til/fil.py' })).toBe('fil.py')
  })

  // Bjørn 17/9-2026: «næsten altid på køre kommando: cd indtil kommandoen er
  // kørt». Linjen viste de første tegn af kommandoen, og næsten hver kommando
  // her begynder med `cd /media/projects/jarvis-v2 && …`. Nu læses kommandoen:
  // scene-sætningen springes over, og der står hvad der faktisk køres.
  it('en kommando læses som en kommando — ikke som de første 48 tegn', () => {
    expect(subjectFromInput({ command: 'cd /media/projects/jarvis-v2 && grep -rn "tool_calls" core' }))
      .toBe('grep tool_calls')
    expect(subjectFromInput({ command: 'sudo -n systemctl restart jarvis-api' }))
      .toBe('systemctl restart')
    expect(subjectFromInput({ command: 'cd /tmp/ocp && cat > fwd.py' })).toBe('cat fwd.py')
    // Kun et mappeskift: så ER det hvad der skete.
    expect(subjectFromInput({ command: 'cd /tmp' })).toBe('cd /tmp')
  })
})

describe('én linje for hele runden', () => {
  it('ét kald → dets egen beskrivelse', () => {
    expect(summarizeRound([t('read_file', { path: 'a.ts' })])).toBe('Læste a.ts')
  })

  it('flere ens → tælles op', () => {
    expect(summarizeRound([
      t('read_file', { path: 'a.ts' }), t('read_file', { path: 'b.ts' }),
    ])).toBe('Læste 2 filer')
  })

  it('blandede → ét led PR. VÆRKTØJ', () => {
    // 14/9: linjen sagde «Kørte 2 værktøjer» — en optælling af hvor mange
    // funktionskald der var, hvilket ikke interesserer nogen. Den gamle
    // forventning står her som det den var: den fattigste mulige beskrivelse
    // af en tur.
    expect(summarizeRound([
      t('read_file', { path: 'a.ts' }), t('bash', { command: 'ls' }),
    ])).toBe('Læste en fil og kørte en kommando')
  })

  it('resultatets EGEN optælling slår antallet af kald', () => {
    // «Ændrede 16 filer» siger mere end «Kørte 3 værktøjer».
    expect(summarizeRound([
      t('edit_file', { path: 'a' }, 'done', 'modified 9 filer'),
      t('edit_file', { path: 'b' }, 'done', 'modified 7 filer'),
    ])).toBe('Redigerede 16 filer')
  })

  it('kører den, står linjen i nutid med prikker', () => {
    expect(summarizeRound([
      t('read_file', { path: 'a' }, 'running'), t('read_file', { path: 'b' }, 'running'),
    ])).toBe('Læser 2 filer…')
  })

  it('vi gætter ikke et tal der ikke står der', () => {
    expect(countFromResult('alt gik fint')).toBeUndefined()
    expect(countFromResult('fandt 12 træffere')).toBe(12)
  })

  it('tom runde giver tom linje — ikke en tom ramme', () => {
    expect(summarizeRound([])).toBe('')
  })
})

// ─────────────────────────────────────────────────────────────────────────
// En blandet runde sagde ingenting (14/9-2026) — 1:1 med mobilen
//
// Bjørn vil have Claude Codes linje: «ran a command, edited 3 files +12 −4».
// Rundelinjen fandtes, men for en BLANDET runde sagde den «Kørte 5
// værktøjer»: en optælling af hvor mange funktionskald der var, hvilket ikke
// interesserer nogen. Hvad der SKETE stod der ikke.
//
// Denne fil er porteret fra mobilen og skal blive ved med at være 1:1 — to
// flader der siger forskelligt om den samme tur er værre end én dårlig linje.
// ─────────────────────────────────────────────────────────────────────────

describe('summarizeRound — blandede runder', () => {
  const t = (name: string, status: 'running' | 'done' = 'done') =>
    ({ type: 'tool_use', name, input: {}, status }) as never

  it('samler pr. vaerktoej i den raekkefoelge de skete', () => {
    expect(summarizeRound([t('bash'), t('edit_file'), t('edit_file')]))
      .toBe('Kørte en kommando og redigerede 2 filer')
  })

  it('tre slags led bindes med komma og «og»', () => {
    expect(summarizeRound([t('bash'), t('read_file'), t('edit_file')]))
      .toBe('Kørte en kommando, læste en fil og redigerede en fil')
  })

  it('kun det FOERSTE led har stort begyndelsesbogstav', () => {
    expect(summarizeRound([t('read_file'), t('bash')]))
      .toBe('Læste en fil og kørte en kommando')
  })

  it('«en» frem for «1» — det er en saetning, ikke en tabel', () => {
    expect(summarizeRound([t('bash'), t('edit_file')]))
      .toBe('Kørte en kommando og redigerede en fil')
  })

  it('et ukendt vaerktoej faar sit eget led og ikke en tavshed', () => {
    expect(summarizeRound([t('bash'), t('et_nyt_vaerktoej')]))
      .toBe('Kørte en kommando og kørte en ting')
  })

  it('en runde der koerer bruger NUTID og slutter med prikker', () => {
    expect(summarizeRound([t('bash', 'running'), t('edit_file', 'running')]))
      .toBe('Kører en kommando og redigerer en fil…')
  })

  it('ensartede runder er UROERTE', () => {
    expect(summarizeRound([t('edit_file'), t('edit_file'), t('edit_file')]))
      .toBe('Redigerede 3 filer')
  })

  it('operator-varianten taeller som samme vaerktoej', () => {
    // `grundnavn` fjerner operator-praefikset. Uden det ville «kørte en
    // kommando og kørte en kommando» staa der — to led om det samme.
    expect(summarizeRound([t('bash'), t('operator_bash')]))
      .toBe('Kørte 2 kommandoer')
  })
})
