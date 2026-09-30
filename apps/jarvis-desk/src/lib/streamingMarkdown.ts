import { scanFences } from './fenceScanner'

/** 29/9-2026: kun en reel, åben linje-fence må holdes tilbage. At tælle
 *  delstrengen ``` slettede almindelig prosa og klippede 4-backtick-blokke.
 *  Afsluttede kodelinjer vises straks; den ufuldstændige sidste linje skjules,
 *  så parseren ikke skifter layout for hvert tegn midt i en linje. */
/**
 * KENDT BEGRAENSNING — accepteret, ikke en fejl (spec punkt 9, 30/9-2026).
 *
 * Et reference-link eller en fodnote hvis DEFINITION ligger paa den anden
 * side af fryse-graensen vises som RAA TEKST mens svaret streamer, og loeses
 * foerst ved finalize. `[a][b]` uden `[b]: …` endnu er ikke et link — det er
 * fire tegn prosa, og det er korrekt markdown.
 *
 * DSH skriver den samme begraensning hoejt om sin egen implementering. Den
 * staar her for at den ikke bliver «opfoert» som en fejl senere: den der ser
 * det, ser noget der ligger i modellen, ikke noget der er gaaet i stykker.
 *
 * Og den anden vej: naar den sidste fence er UDEN en eneste afsluttet linje,
 * falder vi tilbage til hale-vejen og holder hele fencen tilbage. Den vej er
 * verificeret i testen — en dokumenteret begraensning der ikke virker er
 * vaerre end en udokumenteret, fordi ingen leder efter den.
 */
export function stabilizeStreamingMarkdown(md: string): string {
  const spans = scanFences(md)
  const last = spans[spans.length - 1]
  if (!last || last.closed) return md
  const openerEnd = md.indexOf('\n', last.start)
  const completeEnd = md.lastIndexOf('\n')
  if (openerEnd >= 0 && completeEnd > openerEnd) {
    return md.slice(0, completeEnd + 1) + last.marker.repeat(last.length)
  }
  return md.slice(0, last.start).replace(/\n+$/, '')
}
