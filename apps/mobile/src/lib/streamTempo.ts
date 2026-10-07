/**
 * Hvor JAEVNT naar stream-deltaerne frem paa enheden?
 *
 * ## Hvorfor maalingen findes
 *
 * Bjoern 1/10-2026: «man naar sjaeldent at se den streame hans svar — det
 * virker som om det dumper ind — ogsaa hans synteser — men KUN i mobilen.
 * Desk er fin.»
 *
 * De to klienter laeser den SAMME stream paa vidt forskellig vis:
 *
 * - desk: `fetch()` + `response.body.getReader()` — en aegte byte-laeser.
 * - mobil: `react-native-sse`, som henter via `xhr.onreadystatechange` og
 *   `responseText`. Den ser foerst data naar React Natives NATIVE netvaerkslag
 *   fyrer et callback, og det lag samler chunks sammen foerst.
 *
 * Mekanismen er laest i begge klienters kilde. STOERRELSEN er ikke maalt paa en
 * enhed, og uden det tal ved vi ikke om et transport-skifte er besvaeret vaerd —
 * `streamClient` er appens mest kritiske fil.
 *
 * ## Hvad tallet betyder
 *
 * `andel_under_2ms` er det diskriminerende maal. Kommer deltaerne jaevnt, ligger
 * mellemrummene omkring 9–15 ms (serveren leverede median 110 tokens/s 1/10).
 * Samler det native lag dem i bunker, bliver fordelingen TOHOVEDET: mange
 * naer-nul mellemrum inde i en bunke, afbrudt af lange pauser. En hoej andel
 * under 2 ms ER klumpningen.
 *
 * Self-safe: en maaling maa aldrig kunne vaelte en stream. Alt er i try/catch
 * hos kalderen, og hver funktion her er ren bogfoering uden I/O.
 */

let mellemrum: number[] = []
let sidst = 0
let start = 0
let runId = ''

/** Noter at ET event naaede frem. Kaldes for hver parsed SSE-begivenhed. */
export function noterEvent(id?: string): void {
  const nu = Date.now()
  if (id && id !== runId) {
    // Ny koersel: begynd forfra, saa tallet beskriver én tur.
    mellemrum = []
    start = nu
    runId = id
  }
  if (sidst > 0) mellemrum.push(nu - sidst)
  sidst = nu
  if (!start) start = nu
  // Loft: en lang tur maa ikke lade listen vokse frit paa en telefon.
  if (mellemrum.length > 4000) mellemrum = mellemrum.slice(-2000)
}

/** Hent opsummeringen og ryd. `null` naar der ikke er nok til et tal. */
export function hentOgRyd(): Record<string, unknown> | null {
  if (mellemrum.length < 20) return null
  const sorteret = [...mellemrum].sort((a, b) => a - b)
  const p = (andel: number) => sorteret[Math.min(sorteret.length - 1,
    Math.floor(sorteret.length * andel))] ?? 0
  const under2 = sorteret.filter((g) => g < 2).length
  const ud = {
    events: mellemrum.length + 1,
    median_ms: p(0.5),
    p90_ms: p(0.9),
    maks_ms: sorteret[sorteret.length - 1] ?? 0,
    andel_under_2ms: Math.round(1000 * under2 / sorteret.length) / 10,
    varighed_s: Math.round((sidst - start) / 100) / 10,
    run_id: runId,
  }
  mellemrum = []
  sidst = 0
  start = 0
  return ud
}

/** Kun til test. */
export function _nulstil(): void {
  mellemrum = []; sidst = 0; start = 0; runId = ''
}
