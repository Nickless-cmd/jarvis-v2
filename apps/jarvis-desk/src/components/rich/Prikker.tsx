/**
 * Tre prikker der ruller — linjens «og det tager tid».
 *
 * ## Hvorfor de bevæger sig
 *
 * Linjen sagde før «Kører npm test…» med prikker skrevet som TEKST: «.» →
 * «..» → «...», hvert 420. ms, drevet af et interval i JS. De blev lagt til,
 * men de stod stille. Det er kun det halve: et tegn der dukker op siger «der
 * sker noget»; en bølge der ruller gennem prikkerne siger «og det tager tid».
 *
 * Claude Desktop gør det sidste. Tallene her er målt i deres CSS: tre spans,
 * 3 px, forskudt 150 ms, 1,9 s pr. runde, der stiger og falder mens de toner
 * ind og ud. Farven er vores egen (`currentColor`), så prikkerne skifter med
 * linjen de står på — også når linjen er rød.
 *
 * ## Hvorfor det ikke koster et interval
 *
 * Bevægelsen er ren CSS. Før gentegnede komponenten sig hvert 420. ms for at
 * skrive et nyt punktum; nu rører React sig ikke mens prikkerne ruller.
 */

/** Prikkerne. `live` styrer om de findes — en færdig linje har ingen. */
export function Prikker({ live }: { live: boolean }) {
  if (!live) return null
  return (
    <span className="prikker" aria-hidden="true">
      <span />
      <span />
      <span />
    </span>
  )
}

/**
 * «Kører npm test…» → «Kører npm test».
 *
 * Prikkerne er ikke længere tegn i teksten, så en ellipse i enden ville stå
 * dobbelt: «Kører npm test… •••».
 */
export function udenEllipse(tekst: string): string {
  return tekst.replace(/…$/, '')
}
