import { apiFetch, type ApiConfig } from './api'

/** Bjørns egen vej ind i indbakken — den fjerde skriver.
 *
 *  Ruten er `POST /chat/inbox/flag` (bygget 4/10-2026, commit `0223727fd`).
 *  Indtil da lagde bug-ikonet sin tekst i skrivefeltet, og kommentaren i
 *  `Composer` sagde hvorfor: «der skal ingen ny server-route til». Den rute
 *  findes nu, og så skal rapporten derhen hvor den kan ses og lukkes — ikke
 *  ind i en samtale hvor den bliver et spørgsmål Jarvis skal svare på.
 *
 *  INGEN `bruger_id` i kroppen. Serveren tager den fra den autentificerede
 *  kontekst; et felt kalderen vælger er en påstand, ikke proveniens. Ruten
 *  ignorerer et medsendt `bruger_id`, og testen på serveren pinner det.
 *
 *  `bloker` sendes bevidst IKKE. Bjørns afgørelse 4/10 er «synlig men gater
 *  ikke som standard», og et felt der kan spærre for de værktøjer der skulle
 *  rette fejlen er den dead-lock der allerede er målt én gang.
 */
export async function rapporterBug(
  config: ApiConfig,
  titel: string,
  beskrivelse: string,
): Promise<{ id?: string }> {
  return apiFetch<{ status: string; id?: string; bloker?: boolean }>(
    config,
    '/chat/inbox/flag',
    { method: 'POST', body: { titel, beskrivelse } },
  )
}
