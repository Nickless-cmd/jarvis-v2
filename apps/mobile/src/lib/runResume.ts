import type { McRun, McRunStep } from './mcTypes'

export type Udfald = 'kører' | 'lykkedes' | 'fejlede' | 'afbrudt'

export interface RunResume {
  udfald: Udfald
  /** Sekunder. null når starttidspunktet ikke kan læses. */
  sekunder: number | null
  runder: number
  vaerktoejskald: number
  /** De mest brugte værktøjer, flest først. */
  vaerktoejer: { navn: string; antal: number }[]
  godkendelser: number
  /** Det der gik galt — tomt når intet gjorde. */
  fejl: string[]
}

// MÅLT på runtime 12/9-2026, ikke gættet. Et rigtigt run bar: tool.invoked 16,
// runtime.agentic_round_start 9, runtime.visible_run_execution_trace 3,
// tool.force_invoked 2, tool.approval_requested 2, tool_router.decision 1,
// runtime.visible_run_started 1.
const RUNDE = 'runtime.agentic_round_start'
const KALD = new Set(['tool.invoked', 'tool.force_invoked'])
const GODKENDELSE = 'tool.approval_requested'

/**
 * Hvad skete der i dette run?
 *
 * ## Hvorfor et resumé og ikke bare tidslinjen
 *
 * Tidslinjen findes allerede, og den er lang. Spørgsmålet man har når man
 * trykker på et afsluttet run er ikke «hvad skete der i rækkefølge» — det er
 * «gik det godt, hvor længe tog det, og hvad gik galt». Tre linjer i stedet
 * for tres.
 *
 * ## Hvorfor «afbrudt» ikke er «fejlede»
 *
 * Et run nogen selv standsede er ikke en fejl, og at farve de to ens ville
 * gøre farven ubrugelig — man ville se rødt på noget man selv gjorde. Samme
 * skelnen som prikken på Tasks bruger.
 */
export function opsummerRun(run: McRun | null, steps: McRunStep[] = []): RunResume {
  const status = String(run?.status || '').toLowerCase()
  const udfald: Udfald =
    status === 'completed' || status === 'success' ? 'lykkedes'
    : status === 'cancelled' ? 'afbrudt'
    : status === 'failed' || status === 'interrupted' ? 'fejlede'
    : 'kører'

  const taeller = new Map<string, number>()
  let runder = 0
  let kald = 0
  let godkendelser = 0
  const fejl: string[] = []

  for (const s of steps) {
    const k = String(s.kind || '')
    if (k === RUNDE) runder += 1
    else if (KALD.has(k)) {
      kald += 1
      const navn = String(s.tool || '').trim()
      if (navn) taeller.set(navn, (taeller.get(navn) ?? 0) + 1)
    } else if (k === GODKENDELSE) godkendelser += 1
    // Fejl kendes paa TYPEN, ikke paa at ordet «error» staar i en tekst. En
    // besked der NAEVNER en fejl er ikke en fejl - det var derfor foerste
    // udgave talte tool-resultater med ordet «error» i deres output.
    if (/\.(error|failed|failure)$/.test(k) && s.summary) fejl.push(s.summary)
  }

  // Runnets EGET fejlfelt foerst: det er serverens dom, og den vejer tungere
  // end en haendelse undervejs som maaske blev haandteret.
  const egen = String(run?.error || '').trim()
  if (egen) fejl.unshift(egen)

  return {
    udfald,
    sekunder: varighed(run),
    runder,
    vaerktoejskald: kald,
    vaerktoejer: [...taeller.entries()]
      .map(([navn, antal]) => ({ navn, antal }))
      .sort((a, b) => b.antal - a.antal),
    godkendelser,
    fejl,
  }
}

/**
 * Hvor længe kørte det?
 *
 * Et run uden `finished_at` maales mod NU — det kører stadig. Uden den regel
 * ville et aktivt run vise «0 sekunder» for evigt.
 */
export function varighed(run: McRun | null, nu: Date = new Date()): number | null {
  const start = Date.parse(String(run?.started_at || ''))
  if (!Number.isFinite(start)) return null
  const slut = run?.finished_at ? Date.parse(String(run.finished_at)) : nu.getTime()
  if (!Number.isFinite(slut)) return null
  return Math.max(0, Math.round((slut - start) / 1000))
}

/** «2 t 14 min», «3 min 07 s», «42 s». Tom streng når tiden er ukendt. */
export function formatVarighed(sekunder: number | null): string {
  if (sekunder === null) return ''
  if (sekunder < 60) return `${sekunder} s`
  const m = Math.floor(sekunder / 60)
  const s = sekunder % 60
  if (m < 60) return `${m} min ${String(s).padStart(2, '0')} s`
  return `${Math.floor(m / 60)} t ${String(m % 60).padStart(2, '0')} min`
}
