/**
 * Klip en streng uden at braekke et tegn over.
 *
 * `slice()` arbejder paa UTF-16-enheder. Et emoji fylder to, saa et klip midt
 * i parret efterlader en ensom surrogat — og det farlige er ikke det oedelagte
 * tegn, men at ugyldig UTF-8 kan braekke serialiseringen af hele beskeden
 * laengere nede. `Array.from` itererer paa kodepunkter, saa et tegn enten
 * kommer med eller ikke.
 *
 * Ét sted, to brugere (skinnens svar-uddrag og udeladelses-laget), fordi to
 * kopier af den her er to steder fejlen kan komme tilbage.
 */
export function klipTegn(s: string, maks: number): string {
  const tegn = Array.from(s)
  if (tegn.length <= maks) return s
  return tegn.slice(0, Math.max(0, maks - 1)).join('').trimEnd() + '…'
}

/** Antal TEGN, ikke UTF-16-enheder. */
export function tegnTal(s: string): number {
  return Array.from(s).length
}
