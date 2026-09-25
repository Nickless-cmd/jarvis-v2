/** HVORNAAR spoerges der om et genoptagelses-varsel.
 *
 * Reglen har vaeret forkert tre gange i traek, og hver gang af samme grund:
 * den laa flettet ind i `stream.status` inde i `ChatView`, hvor den kun kunne
 * efterproeves ved at bygge programmet og se efter. De tre:
 *
 *   1. `status === 'idle'` — men reduceren saetter `'done'` naar et run
 *      slutter. `'idle'` gaelder kun foer det allerfoerste run i en
 *      klient-session, altsaa i en samtale man aldrig har brugt. Varslet
 *      kunne dermed kun vises de steder hvor der aldrig er noget at vise.
 *   2. Der blev spurgt én gang pr. komponent-levetid, saa et varsel der
 *      opstod bagefter blev aldrig hentet.
 *   3. `forrige === 'working'` som tegn paa at en tur sluttede — men
 *      `useRammeReducer` samler opdateringer til én pr. frame, saa
 *      mellemtilstanden `'working'` findes aldrig i en render.
 *
 * Og den fjerde, maalt 25/9-2026 i journalen paa CT105: effekten sprang fra
 * paa `status === 'working' || 'reconnecting'`. Ved mount fyrede `warm` (som
 * kun afhaenger af `[settings, sessionId]`) 22:49:31, mens varslet slet ikke
 * blev hentet — i 11½ time. Naar en betingelse har taget fejl fire gange, er
 * problemet ikke betingelsen, men at den ikke kunne proeves.
 *
 * Derfor: ingen afhaengighed af om der koerer noget. Er der et live run,
 * svarer serveren om det, og et opgivet run fra i gaar er netop det SSE
 * aldrig kan fortaelle om. Der spoerges ved sessionsaabning — praecis som
 * `warm`, den eneste nabo-effekt der beviseligt virker — og igen naar en tur
 * slutter, fordi det er det oejeblik et nyt varsel kan vaere opstaaet.
 */

/** Statusser der betyder «en tur sluttede lige». */
const AFSLUTTEDE = new Set(['done', 'interrupted', 'error'])

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
