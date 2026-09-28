/** HVORNAAR spoerges der om et genoptagelses-varsel.
 *
 * Tvilling til desks `lib/genoptagelsesVarsel.ts`. Reglen er den samme, og den
 * er skrevet dyrt: i desk tog den fejl FIRE gange, hver gang fordi den laa
 * flettet ind i `stream.status` inde i en komponent, hvor den kun kunne
 * efterproeves ved at bygge programmet og se efter.
 *
 *   1. `status === 'idle'` — men reduceren saetter `'done'` naar et run
 *      slutter. `'idle'` gaelder kun foer det allerfoerste run.
 *   2. Der blev spurgt én gang pr. komponent-levetid, saa et varsel der
 *      opstod bagefter blev aldrig hentet.
 *   3. `forrige === 'working'` som tegn paa at en tur sluttede — men
 *      opdateringer samles til én pr. frame, saa mellemtilstanden findes
 *      aldrig i en render.
 *   4. Effekten sprang fra paa at der KOERTE noget. Et opgivet run fra i gaar
 *      er netop det SSE aldrig kan fortaelle om.
 *
 * Derfor: ingen afhaengighed af om der koerer noget. Der spoerges ved
 * sessionsaabning og igen naar en tur slutter, fordi det er det oejeblik et
 * nyt varsel kan vaere opstaaet.
 *
 * Hvorfor mobilen overhovedet faar den: maalt 28/9-2026 var der NUL
 * forekomster af «recovery» i hele mobil-kildekoden. Desk fik banneret 25/9.
 * Paa telefonen stoppede en koersel der gik i genoptagelse bare — med den
 * tekst den naaede, og ingen forklaring. Samtidig gik andelen af koersler der
 * ikke naar «completed» fra 2-8 % til 13-21 % (20.-28. sep), drevet af
 * `pending-tool-intent`: «Jarvis havde stadig et vaerktoejskald klar».
 */

/** Statusser der betyder «en tur sluttede lige».
 *
 * `hung` er med, selv om den ikke er en afslutning: det er praecis den
 * tilstand hvor skaermen staar stille og brugeren tror turen er doed. Er der
 * et varsel at hente, er det dér det skal siges.
 */
const AFSLUTTEDE = new Set(['done', 'interrupted', 'error', 'hung'])

export type VarselSpoergsmaal = {
  /** Hent varslet nu. */
  spoerg: boolean
  /** Glem at vi har spurgt for denne session — en tur sluttede. */
  nulstil: boolean
}

export function skalSpoergeOmVarsel(arg: {
  /** `stream.status` ved forrige koersel af effekten. */
  forrige: string
  /** `stream.status` nu. */
  status: string
  sessionId: string | null
  /** Sessionen vi sidst spurgte for, eller null. */
  alleredeSpurgt: string | null
}): VarselSpoergsmaal {
  // Enhver ANKOMST i en afsluttet tilstand betyder at en tur sluttede. Ikke
  // «forrige var working» — den mellemtilstand ser en effekt aldrig.
  const nulstil = arg.forrige !== arg.status && AFSLUTTEDE.has(arg.status)
  if (!arg.sessionId) return { spoerg: false, nulstil }
  const spurgt = nulstil ? null : arg.alleredeSpurgt
  return { spoerg: spurgt !== arg.sessionId, nulstil }
}
