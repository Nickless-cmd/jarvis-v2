/**
 * Forslag til komponisten — et bud på den NÆSTE besked.
 *
 * ## Hvorfor ikke en fortsættelse af det man skriver
 *
 * Den første form var Claude Codes: grå tekst efter markøren, der foreslog
 * resten af sætningen mens man skrev. Bjørn 17/9-2026: «det kommer dumpende
 * mens jeg skriver, det er virkelig træls». Et forslag der konkurrerer med
 * hans egne ord er en afbrydelse; et forslag der venter i det tomme felt er
 * et tilbud.
 *
 * Mobilen havde længe fortsættelses-formen: den sendte hans HALVSKREVNE
 * udkast og bad en lokal model gætte resten af sætningen. Bjørn 24/9-2026:
 * «lige nu er det en model der gætter på mine næste ord udfra det jeg
 * skriver, det er lidt mærkeligt». Formen er nu den samme som desk: ÉT
 * forslag, hentet når feltet er TOMT, bygget på samtalen — og når Jarvis selv
 * har lagt et forslag i sin tur, er det HANS ord der møder brugeren, ikke en
 * lille models gæt.
 *
 * ## Hvorfor en linje over feltet, og ikke pladsholder-tekst
 *
 * Desk viser forslaget dér hvor pladsholderen står. React Natives `TextInput`
 * kan ikke tegne inde i feltet uden at lægge en usynlig kopi ovenpå og holde
 * de to i synk — to sandheder om hvad der står, der falder fra hinanden ved
 * hvert tastetryk. En linje over feltet siger det samme, kan trykkes på med
 * tommelfingeren og kan læses op af en skærmlæser. Samme forslag, to flader.
 *
 * ## Hvad der ALDRIG sker
 *
 * Kaldet går til `/composer/suggest`. Med et tomt udkast og en session svarer
 * serveren med samtale-kontekst — og med Jarvis' eget forslag først, hvis han
 * har lagt et. Et halvskrevet udkast forlader aldrig maskinen, for der sendes
 * intet udkast: feltet er tomt når vi spørger.
 */
import type { ApiConfig } from './types'

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
 * Hvor længe der ventes før der spørges.
 *
 * `aktiv` bliver sand i samme øjeblik et svar er færdigt — dér er GPU'en
 * stadig varm fra turen. Pausen lader den komme fri, og den koster intet:
 * feltet er tomt, så der er ingen der venter på forslaget. Samme tal som desk.
 */
export const HENT_PAUSE_MS = 700

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
    const d = (await r.json()) as {
      forslag?: unknown
      forslag_id?: unknown
      kilde_besked_id?: unknown
    }
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
    }).catch(() => {
      /* et tabt valg er telemetri, ikke en fejl */
    })
  } catch {
    /* komponisten skriver videre uanset hvad */
  }
}
