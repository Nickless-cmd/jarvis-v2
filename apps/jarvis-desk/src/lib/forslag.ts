/**
 * Forslag til komponisten — hvad der kunne skrives videre, mens man skriver.
 *
 * ## Hvorfor ghost-tekst her, og en linje på mobilen
 *
 * Claude Code viser forslaget som grå tekst efter markøren. Mobilen kan det
 * ikke: React Natives `TextInput` kan ikke tegne inde i feltet, så der vælger
 * man en linje man trykker på. Desk er en rigtig DOM-`<textarea>`, så her kan
 * den oprindelige form bruges. Det er ikke to funktioner — det er den samme,
 * i den form fladen tillader.
 *
 * ## Hvorfor klienten selv siger fra
 *
 * Serveren afviser de samme tilfælde. At gentage reglen her er ikke
 * dobbeltarbejde: hvert tastetryk der ikke bliver til et kald, er GPU der ikke
 * konkurrerer med det synlige svar. Husets erfaring står skrevet ned —
 * recall-embeds køede 28–91 sekunder bag et svar på samme ollama.
 */
import type { ApiConfig } from './api'

/** Under det er der intet at gætte på. Samme tal som serveren. */
export const MIN_TEGN = 8
/** Over det ved han hvad han vil. Samme tal som serveren. */
export const MAKS_UDKAST = 600
/** Hvor længe der ventes efter sidste tastetryk. */
export const PAUSE_MS = 350

const FAERDIG = /[.!?:;]\s*$/

/**
 * Er det værd at spørge om et forslag?
 *
 * Slutter sætningen på tegnsætning, er brugeren færdig — at foreslå videre dér
 * er at tale i munden på ham.
 */
export function boerSpoerge(udkast: string): boolean {
  const u = (udkast ?? '').trim()
  if (u.length < MIN_TEGN || u.length > MAKS_UDKAST) return false
  if (FAERDIG.test(u)) return false
  return true
}

/**
 * Sæt forslaget sammen med udkastet.
 *
 * Bevarer udkastets EGEN afslutning: skriver man med et mellemrum til sidst,
 * skal forslaget ikke tilføje endnu et. Serveren hæfter allerede et mellemrum
 * på fortsættelsen, så to ville give «tjekke  det».
 */
export function saetSammen(udkast: string, forslag: string): string {
  const u = udkast ?? ''
  const f = forslag ?? ''
  if (!f) return u
  if (u.endsWith(' ') && f.startsWith(' ')) return u + f.slice(1)
  return u + f
}

/**
 * Hent et forslag. Tom streng ved enhver fejl — komponisten skal kunne skrives
 * i uanset hvad der sker med modellen.
 *
 * `signal` afbryder et kald der er blevet uinteressant, fordi brugeren har
 * skrevet videre. Uden det ville et langsomt svar kunne lande ovenpå et nyere
 * og foreslå noget der passede til en sætning der ikke findes mere.
 *
 * Ingen retries: et forslag der ikke kom i første forsøg er allerede for sent.
 */
export async function hentForslag(
  config: ApiConfig,
  udkast: string,
  signal?: AbortSignal,
): Promise<string> {
  if (!boerSpoerge(udkast)) return ''
  try {
    const r = await fetch(`${config.apiBaseUrl}/composer/suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(config.authToken ? { Authorization: `Bearer ${config.authToken}` } : {}),
      },
      body: JSON.stringify({ udkast }),
      signal,
    })
    if (!r.ok) return ''
    const d = (await r.json()) as { forslag?: unknown }
    return typeof d?.forslag === 'string' ? d.forslag : ''
  } catch {
    return ''
  }
}
