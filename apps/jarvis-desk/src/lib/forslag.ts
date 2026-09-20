/**
 * Auto-forslag til komponisten — et bud på den NÆSTE besked.
 *
 * ## Hvorfor det ikke er en fortsættelse af det man skriver
 *
 * Den første form var Claude Codes: grå tekst efter markøren, der foreslog
 * resten af sætningen mens man skrev. Bjørn 17/9-2026: «det kommer dumpende
 * mens jeg skriver, det er virkelig træls» — og «auto suggest skal jo være ud
 * fra konteksten af din besked». Et forslag der konkurrerer med hans egne ord
 * er en afbrydelse; et forslag der venter i det tomme felt er et tilbud.
 *
 * Så desk henter ÉT forslag når feltet er tomt, bygget på samtalen, og viser
 * det dér hvor pladsholderen står. Tab gør det til rigtig tekst.
 *
 * Mobilen beholder fortsættelses-formen i sin egen `lib/forslag.ts`: der er
 * ingen pladsholder-plads at stå i, og React Natives `TextInput` kan ikke
 * tegne inde i feltet. Samme endpoint, to former, fordi fladerne er forskellige.
 *
 * ## Hvad der ALDRIG sker
 *
 * Kaldet går til `/composer/suggest`, som spørger den lokale ollama. Hverken
 * udkast eller samtale forlader maskinen, og der er ingen udgift at bogføre.
 */
import type { ApiConfig } from './api'

/** Et forslag og det klienten skal bruge for at kunne melde valget tilbage. */
export interface Forslag {
  tekst: string
  /** Serverens id for netop DETTE forslag. Tomt = intet at melde tilbage om. */
  id: string
  /** Den assistent-besked forslaget blev udledt af. */
  kildeBeskedId: string
}

export const INTET_FORSLAG: Forslag = { tekst: '', id: '', kildeBeskedId: '' }

/**
 * Hent et forslag til den næste besked. Tomt ved enhver fejl —
 * komponisten skal kunne skrives i uanset hvad der sker med modellen.
 *
 * `signal` afbryder et kald der er blevet uinteressant, fordi han nåede at
 * skrive selv eller skifte samtale. Uden det ville et langsomt svar kunne
 * lande ovenpå og foreslå noget der hørte til et andet sted.
 *
 * Ingen retries: et forslag der ikke kom i første forsøg er allerede for sent.
 */
export async function hentNaesteForslag(
  config: ApiConfig,
  sessionId: string,
  signal?: AbortSignal,
): Promise<Forslag> {
  if (!sessionId) return INTET_FORSLAG
  try {
    const r = await fetch(`${config.apiBaseUrl}/composer/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
      },
      body: JSON.stringify({ udkast: '', session_id: sessionId }),
      signal,
    })
    if (!r.ok) return INTET_FORSLAG
    const d = (await r.json()) as { forslag?: unknown; forslag_id?: unknown; kilde_besked_id?: unknown }
    const tekst = typeof d?.forslag === 'string' ? d.forslag.trim() : ''
    if (!tekst) return INTET_FORSLAG
    return {
      tekst,
      id: typeof d?.forslag_id === 'string' ? d.forslag_id : '',
      kildeBeskedId: typeof d?.kilde_besked_id === 'string' ? d.kilde_besked_id : '',
    }
  } catch {
    return INTET_FORSLAG
  }
}

/** Hvad der skete med et forslag. Se `core/runtime/db_composer_choice.py`. */
export type Valg = 'vist' | 'accepteret' | 'afvist' | 'eget'

/**
 * Meld tilbage hvad der skete med et forslag.
 *
 * Bjørn 20/9-2026: «vi skal gemme brugerens valg, dvs. om de brugte den
 * suggested (tab) i composer eller skrev der egen besked så næste forslag
 * bliver mere mig/målrettet».
 *
 * **Hans egen tekst sendes aldrig med.** Skriver han selv, er beskeden
 * `eget` — ét bit om at forslaget ikke blev brugt, og intet om hvad han så
 * skrev. Det eneste tekstlige i kaldet er forslagets egne ord, som serveren
 * selv har fundet på.
 *
 * Fejler aldrig, og der ventes ikke på svaret: et valg der ikke nåede frem,
 * må aldrig kunne stoppe en besked.
 */
export function meldValg(
  config: ApiConfig,
  forslag: Forslag,
  valg: Valg,
  sessionId: string,
): void {
  if (!forslag.id || !sessionId) return
  try {
    void fetch(`${config.apiBaseUrl}/composer/choice`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
      },
      body: JSON.stringify({
        forslag_id: forslag.id,
        session_id: sessionId,
        forslag: forslag.tekst,
        kilde_besked_id: forslag.kildeBeskedId,
        valg,
      }),
      keepalive: true,
    }).catch(() => { /* et tabt valg er telemetri, ikke en fejl */ })
  } catch {
    /* komponisten skriver videre uanset hvad */
  }
}
