/** Hvor lang tid ét trin i prik-sekvensen varer. */
export const TRIN_MS = 420

/**
 * «.» → «..» → «...» → «.» …
 *
 * ## Hvorfor prikker og ikke et lys
 *
 * Fordi ordet er kort og fast. Et lys der glider gennem «Tænker» er den samme
 * bevægelse hver eneste gang og siger intet om at tiden går; prikker der
 * lægges til gør. De to tegn er ikke i modstrid — lyset siger «her arbejdes»,
 * prikkerne siger «og det tager tid».
 *
 * ## Hvorfor bredden er fast
 *
 * Etiketten skal ikke hoppe. Ved at fylde op med tynde mellemrum står
 * teksten efter prikkerne stille, uanset hvor i sekvensen man er.
 */
export function prikker(trin: number, maks = 3): string {
  const n = ((Math.floor(trin) % maks) + maks) % maks + 1
  // U+2009 THIN SPACE. Et almindeligt mellemrum bliver ofte klippet væk i
  // slutningen af en tekst; et tyndt gør ikke, og det fylder omtrent som et
  // punktum.
  return '.'.repeat(n) + ' '.repeat(maks - n)
}
