/**
 * Forslag til komponisten — hvad der kunne skrives videre.
 *
 * ## Hvorfor en linje man trykker på, og ikke ghost-tekst
 *
 * Claude Code viser forslaget som grå tekst efter markøren. Det kræver at man
 * kan tegne inde i selve inputtet, og React Natives `TextInput` kan det ikke
 * uden at man lægger en usynlig kopi ovenpå og holder de to i synk — to
 * sandheder om hvad der står, og de falder fra hinanden ved hvert tastetryk.
 *
 * En linje over feltet siger det samme, kan trykkes på med tommelfingeren og
 * kan læses op af en skærmlæser. Den er ikke et kompromis; den er den rigtige
 * form på en telefon.
 *
 * ## Hvorfor klienten selv siger fra
 *
 * Serveren afviser allerede de samme tilfælde. At gentage reglen her er ikke
 * dobbeltarbejde: hvert tastetryk der ikke bliver til et kald, er GPU der ikke
 * konkurrerer med det synlige svar. Huset har den erfaring skrevet ned —
 * recall-embeds køede 28–91 sekunder bag et svar på samme ollama.
 */

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
 * Hent et forslag. Tom streng ved enhver fejl — komponisten skal kunne
 * skrives i uanset hvad der sker med modellen.
 *
 * `signal` gør det muligt at afbryde et kald der er blevet uinteressant, fordi
 * brugeren har skrevet videre. Uden det ville et langsomt svar kunne lande
 * ovenpå et nyere og foreslå noget der passede til en sætning der ikke findes
 * mere.
 */
export async function hentForslag(
  base: string,
  token: string,
  udkast: string,
  signal?: AbortSignal
): Promise<string> {
  if (!boerSpoerge(udkast)) return ''
  try {
    const r = await fetch(`${base}/composer/suggest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
      body: JSON.stringify({ udkast }),
      signal
    })
    if (!r.ok) return ''
    const d = (await r.json()) as { forslag?: unknown }
    return typeof d?.forslag === 'string' ? d.forslag : ''
  } catch {
    return ''
  }
}
