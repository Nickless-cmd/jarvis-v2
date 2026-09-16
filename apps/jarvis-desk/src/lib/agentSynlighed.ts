/**
 * Hvornår står en agent fremme i Miljø-feltet?
 *
 * Bjørn 16/9-2026: «underagenter skal kun vise agenter når de er aktive …
 * hvis agenten fuldfører sin opgave forsvinder den igen … hvis fejl eller han
 * ikk selv kan stoppe den så bliver den hængende synlig … ellers er feltet kun
 * synligt når der er aktive agenter.»
 *
 * Feltet er altså ikke en historik. Det er en liste over det der KRÆVER hans
 * opmærksomhed: noget der kører, og noget der gik galt. En agent der gjorde
 * sit arbejde færdigt er ikke nyt for nogen.
 *
 * De faktiske statusser i agent_registry (målt 16/9-2026): completed 271,
 * cancelled 17, expired 17, planned 1 — plus failed/starting på kørsels-
 * niveau. Reglen er skrevet efter dem, ikke efter gætværk.
 */

/** Kører, eller venter på at komme i gang. Ikke færdig. */
const AKTIVE = new Set([
  'active', 'running', 'queued', 'starting', 'waiting', 'planned', 'suspended',
])

/** Sluttede, men ikke af sig selv — derfor bliver den hængende.
 *
 * `cancelled` står her efter Bjørns dom 16/9-2026. Jeg havde regnet den som en
 * pæn slutning — «nogen tog en beslutning, den er ikke uafsluttet» — og spurgte
 * om det var rigtigt. Det var det ikke: en annulleret agent nåede ikke sin
 * opgave, og hvad der ikke blev gjort færdigt, skal man kunne se. Kun en agent
 * der LØSTE sin opgave forsvinder. */
const HAENGER = new Set([
  'failed', 'error', 'expired', 'timeout', 'timed_out', 'stuck', 'orphaned',
  'cancelled', 'canceled', 'aborted', 'interrupted',
])

/** Løste sin opgave. Forsvinder — det er det eneste udfald der ikke er nyt. */
const FAERDIGE = new Set([
  'completed', 'succeeded', 'success', 'done', 'finished',
])

export function agentSkalStaaFremme(status?: string): boolean {
  const s = String(status || '').trim().toLowerCase()
  // Tom status = en dispatch der er slut uden at efterlade spor om agenten.
  // Der er intet at handle på, så den forsvinder med de andre færdige.
  if (!s) return false
  if (FAERDIGE.has(s)) return false
  if (AKTIVE.has(s) || HAENGER.has(s)) return true
  // En status vi ikke kender er IKKE det samme som «færdig». At skjule den
  // ville betyde at en ny tilstand i runtimen forsvandt fra skærmen uden at
  // nogen opdagede det. Hellere en række for meget end en tavs udeladelse.
  return true
}

/** Kører den lige nu? Bruges til den pulserende markering og til polling. */
export function agentErAktiv(status?: string): boolean {
  return AKTIVE.has(String(status || '').trim().toLowerCase())
}
