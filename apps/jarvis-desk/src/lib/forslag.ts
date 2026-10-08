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
 * Mobilen viser forslaget på en linje over feltet i stedet: der er ingen
 * pladsholder-plads at stå i, og React Natives `TextInput` kan ikke tegne inde
 * i feltet. Samme forslag, to flader.
 *
 * ## Hvad der ALDRIG sker
 *
 * Kaldet går til `/composer/suggest`. Siden 28/9-2026 kommer forslaget
 * udelukkende fra Jarvis selv: den lokale model blev droppet, og uden et eget
 * forslag står feltet tomt. Der sendes intet udkast — feltet er tomt når vi
 * spørger — og der er ingen udgift at bogføre, for der kaldes ingen model.
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
 * Absolut sti på api-basen — med ÉN skråstreg.
 *
 * `absolutApiUrl` i `api.ts` gør det samme, men den importeres IKKE her: denne
 * fil deler kun en TYPE med api-modulet. Et værdi-import ville tvinge hver test
 * der mocker `./api` til også at mocke den — målt 8/10-2026 gav det to
 * utilsigtede fejl i ChatView-testen, kastet fra en timer efter testen var
 * slut, fordi mocken ikke kendte eksporten.
 *
 * Begge konventioner skal virke: desk gemmer `https://api.srvlab.dk/`
 * (`SetupScreen`), mobilen uden skråstreg. Strengsammensætning gav derfor
 * `//composer/suggest` i desk — en sti der ikke matcher nogen API-rute, falder
 * igennem til StaticFiles-mountet og svarer 405.
 */
function sti(config: ApiConfig, vej: string): string {
  const base = String(config?.apiBaseUrl || '').replace(/\/+$/, '')
  return base ? `${base}${vej}` : ''
}

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
  // `sti` og ikke strengsammensætning. apiBaseUrl slutter på en skråstreg i
  // desk (`SetupScreen`), så `${base}/composer/suggest` gav
  // `//composer/suggest`. Den sti matcher ingen API-rute, falder igennem til
  // StaticFiles-mountet — som kun tillader GET/HEAD — og svarer 405. Tavst,
  // fordi `!r.ok` nedenfor giver INTET_FORSLAG uden at logge. Målt 8/10-2026:
  // desk 31 kald, alle 405 · mobilen 45 kald, alle 200. Det var derfor
  // forslaget nåede mobilen og ikke desk.
  const url = sti(config, '/composer/suggest')
  if (!url) return INTET_FORSLAG
  try {
    const r = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
      },
      body: JSON.stringify({ session_id: sessionId }),
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
  const url = sti(config, '/composer/choice')
  if (!url) return
  try {
    void fetch(url, {
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
