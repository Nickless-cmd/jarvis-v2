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

/**
 * Hent et forslag til den næste besked. Tom streng ved enhver fejl —
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
): Promise<string> {
  if (!sessionId) return ''
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
    if (!r.ok) return ''
    const d = (await r.json()) as { forslag?: unknown }
    return typeof d?.forslag === 'string' ? d.forslag.trim() : ''
  } catch {
    return ''
  }
}
