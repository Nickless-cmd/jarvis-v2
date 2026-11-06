/**
 * Deep-link fra en web-push (6/11-2026).
 *
 * Service workeren bygger `/?session=<id>` naar brugeren trykker paa en
 * notifikation (`src/pwa/service-worker.ts`). Men INGEN i appen laeste den
 * parameter: klikket fokuserede vinduet, navigerede til en URL appen
 * ignorerede, og notifikationen lukkede sig. Fra brugerens side «forsvandt»
 * notifikationen uden at foere nogen steder hen.
 *
 * Maalt foer fixet: strengen `?session=` fandtes kun i service-worker.ts —
 * nul laesere i appen. Det er praecis den fejlform hvor afsenderen er bygget
 * og modtageren aldrig blev det.
 *
 * Funktionen er trukket ud her, saa den kan testes uden at rendere hele App.
 */

/** Session-id fra `?session=`, eller `null` naar der ikke er nogen. */
export function sessionFraUrl(sok: string): string | null {
  if (!sok) return null
  const params = new URLSearchParams(sok)
  const id = params.get('session')
  return id && id.trim() ? id.trim() : null
}

/**
 * Fjern `session` fra query-strengen og returner den rene URL.
 *
 * Uden dette ville et refresh (eller en ny navigation) springe til den samme
 * samtale igen — deep-linket skal virke ÉN gang, ikke hver gang appen aabnes.
 */
export function urlUdenSession(sok: string, sti: string, hash: string): string {
  const params = new URLSearchParams(sok)
  params.delete('session')
  params.delete('routine')
  const rest = params.toString()
  return `${sti}${rest ? `?${rest}` : ''}${hash}`
}

/**
 * Rutine-id fra `?routine=`, eller `null`.
 *
 * Et rutine-run lever ikke i en chat-session (`routine_runs` har ingen
 * `session_id`), saa et rutine-push kan ikke pege paa `?session=`. Foer dette
 * faldt service workeren tilbage til '/', og trykket foerte til forsiden —
 * praecis den «notifikationen forsvandt»-oplevelse.
 */
export function routineFraUrl(sok: string): string | null {
  if (!sok) return null
  const id = new URLSearchParams(sok).get('routine')
  return id && id.trim() ? id.trim() : null
}
