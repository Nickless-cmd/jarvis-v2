import type { McRun } from './mcTypes'

/**
 * Baner der er BJØRNS egne ture. Alt andet kørte uden at han bad om det.
 *
 * Målt på runtime 12/9-2026 over 18.202 runs: `primary` 17.866, `agent` 301,
 * `local` 19, `visible` 2. Hans egne ture logges under `primary` — ikke under
 * `visible`, som navnet ellers lover og som kun har to rækker i alt.
 */
const EGNE_BANER = new Set(['primary', 'visible'])

/**
 * Statusser der betyder «den nåede ikke i mål».
 *
 * `cancelled` er IKKE med: den betyder at nogen afbrød med vilje, og en prik
 * for noget man selv har standset er støj. `interrupted` og `failed` er
 * derimod ting der skete uden at nogen valgte dem — 323 og 262 i alt.
 */
const UAFSLUTTEDE = new Set(['interrupted', 'failed'])

export function erAutonom(run: McRun): boolean {
  return !EGNE_BANER.has(String(run.lane || '').toLowerCase())
}

export function erAfbrudt(run: McRun): boolean {
  return UAFSLUTTEDE.has(String(run.status || '').toLowerCase())
}

/**
 * Skal Tasks-fanen bære en prik?
 *
 * Samme kontrakt som Godkend: prikken siger «her er noget du ikke har set på»,
 * ikke «her findes data». Godkend tæller det der VENTER; her er det to ting
 * man ikke selv satte i gang:
 *
 *   autonome  — han arbejdede uden at blive spurgt, og resultatet er værd at se
 *   afbrudte  — noget stoppede undervejs
 *
 * Listen er allerede afgrænset til de seneste (20 fra `fetchRuns`), så prikken
 * kan ikke komme til at lyse på noget fra sidste måned. Det er med vilje at
 * grænsen ligger dér frem for i et tidsfilter her: så er der ét sted der
 * bestemmer hvad «for nylig» betyder.
 */
export function taelOpgaverDerKalder(runs: McRun[] | null | undefined): number {
  return (runs || []).filter((r) => erAutonom(r) || erAfbrudt(r)).length
}
