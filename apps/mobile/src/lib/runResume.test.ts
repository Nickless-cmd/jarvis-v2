import { formatVarighed, opsummerRun, varighed } from './runResume'
import type { McRun, McRunStep } from './mcTypes'

const run = (o: Partial<McRun> = {}): McRun => ({
  run_id: 'r1', lane: 'primary', provider: null, model: null,
  status: 'completed', started_at: '2026-09-12T10:00:00Z',
  finished_at: '2026-09-12T10:02:30Z', text_preview: null, ...o,
})
const s = (kind: string, o: Partial<McRunStep> = {}): McRunStep =>
  ({ kind, at: '2026-09-12T10:00:01Z', summary: '', ...o })

it('taeller runder, kald og godkendelser fra de VIRKELIGE event-typer', () => {
  // Maalt paa runtime 12/9-2026: et rigtigt run bar tool.invoked,
  // runtime.agentic_round_start, tool.force_invoked, tool.approval_requested.
  const r = opsummerRun(run(), [
    s('runtime.agentic_round_start'), s('runtime.agentic_round_start'),
    s('tool.invoked', { tool: 'bash' }), s('tool.force_invoked', { tool: 'bash' }),
    s('tool.invoked', { tool: 'read_file' }),
    s('tool.approval_requested'),
    s('runtime.visible_run_started'),
  ])
  expect(r.runder).toBe(2)
  expect(r.vaerktoejskald).toBe(3)
  expect(r.godkendelser).toBe(1)
  expect(r.vaerktoejer).toEqual([{ navn: 'bash', antal: 2 }, { navn: 'read_file', antal: 1 }])
})

it('AFBRUDT er ikke det samme som FEJLET', () => {
  // Et run nogen selv standsede er ikke en fejl, og at farve de to ens ville
  // goere farven ubrugelig.
  expect(opsummerRun(run({ status: 'cancelled' })).udfald).toBe('afbrudt')
  expect(opsummerRun(run({ status: 'failed' })).udfald).toBe('fejlede')
  expect(opsummerRun(run({ status: 'interrupted' })).udfald).toBe('fejlede')
  expect(opsummerRun(run({ status: 'completed' })).udfald).toBe('lykkedes')
  expect(opsummerRun(run({ status: 'running' })).udfald).toBe('kører')
})

it('runnets EGET fejlfelt staar foerst', () => {
  // Serverens dom vejer tungere end en haendelse undervejs som maaske blev
  // haandteret.
  const r = opsummerRun(run({ status: 'failed', error: 'kvote opbrugt' }), [
    s('tool.error', { summary: 'read_file fejlede' }),
  ])
  expect(r.fejl).toEqual(['kvote opbrugt', 'read_file fejlede'])
})

it('en besked der NAEVNER en fejl er ikke en fejl', () => {
  // Foerste udgave ledte efter ordet «error» i teksten og talte dermed
  // vaerktoejs-output med.
  const r = opsummerRun(run(), [
    s('tool.invoked', { tool: 'bash', summary: 'grep -r "error" i loggen' }),
  ])
  expect(r.fejl).toEqual([])
})

it('et KOERENDE run maales mod nu, ikke mod nul', () => {
  const nu = new Date('2026-09-12T10:05:00Z')
  expect(varighed(run({ finished_at: null }), nu)).toBe(300)
})

it('varigheden er slut minus start', () => {
  expect(varighed(run())).toBe(150)
})

it('uden starttid er varigheden UKENDT, ikke nul', () => {
  expect(varighed(run({ started_at: '' }))).toBeNull()
  expect(formatVarighed(null)).toBe('')
})

it('formaterer i den enhed man kan bruge', () => {
  expect(formatVarighed(42)).toBe('42 s')
  expect(formatVarighed(187)).toBe('3 min 07 s')
  expect(formatVarighed(8040)).toBe('2 t 14 min')
})

it('et run UDEN skridt giver stadig et resume', () => {
  const r = opsummerRun(run(), [])
  expect(r.udfald).toBe('lykkedes')
  expect(r.runder).toBe(0)
  expect(r.fejl).toEqual([])
})
