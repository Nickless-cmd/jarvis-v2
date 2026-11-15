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
  return lukAabneMarkeringer(stabilizeFences(md))
}

function stabilizeFences(md: string): string {
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

/**
 * Lukker en markering der er ved at blive skrevet (14/11-2026).
 *
 * ## Hvorfor den findes
 *
 * Bjørn: «hvorfor knækker markdown inde i turhoved for det meste, men lykkes
 * enkelte gange?» Målt: det er ikke folden og ikke streaming. Den SAMME
 * halve tekst giver rå `**` både med og uden `streaming` — og den komplette
 * tekst er pæn i begge tilstande. Variablen er om teksten er HEL.
 *
 * En tekst der skrives tegn for tegn er uundgåeligt halv i et vindue: hver
 * `**fed**` har et øjeblik hvor der kun står `**fed`. Uden reparation vises
 * stjernerne råt, og det ser ud som om rendereren er i stykker. Derfor
 * «for det meste» — man ser arbejdet mens det sker.
 *
 * Svaret uden for folden rammes ikke, fordi det først vises når det er
 * færdigt (pacet). Det er samme mekanisme, forskelligt tidspunkt.
 *
 * ## Hvad den IKKE gør
 *
 * Kun `**`, `~~`, `$` (med matematik-værn) og enkel inline-code. Ikke `*`
 * eller `_`: en enkelt stjerne eller underscore i dansk prosa er oftest ikke
 * en markering, og en gættet lukning ville gøre skade i stedet for at undgå
 * den. Kode-fences tælles ikke med — kode skal vises som den er skrevet.
 *
 * KENDT BEGRÆNSNING: `**` inde i inline-code tælles med. Det kræver at
 * markeringen er åben på samme tid, og resultatet er da en synlig `**` mere
 * i et kort vindue — ikke en ødelagt flade.
 */
export function lukAabneMarkeringer(md: string): string {
  // Fence-områder erstattes med mellemrum af samme længde, så positioner og
  // længder er uændrede — vi tæller kun i den synlige prosa.
  const spans = scanFences(md)
  let synlig = md
  for (const s of spans) {
    synlig = synlig.slice(0, s.start) + ' '.repeat(s.end - s.start) + synlig.slice(s.end)
  }

  let ud = md
  const stjerner = (synlig.match(/\*\*/g) ?? []).length
  if (stjerner % 2 === 1) ud += '**'
  // Efter en mulig `**`-lukning: backticks tælles på den oprindelige tekst,
  // så de to tællinger ikke påvirker hinanden.
  // Kun ENKELTE backticks er inline-kode. En run på tre eller flere er en
  // fence-agtig sekvens, og `` ``` `` midt i prosa er tre tegn tekst — den
  // må ikke tælles som en åben markering. (Fanget af en eksisterende test:
  // «Brug ``` for kode.» fik ellers en fjerde backtick hængt på.)
  const runs = synlig.match(/`+/g) ?? []
  const ticks = runs.filter((r) => r.length === 1).length
  if (ticks % 2 === 1) ud += '`'

  // `~~` (GFM-gennemstregning) — samme regel som `**`: et ulige antal betyder
  // at den sidste er ved at blive skrevet. Målt 15/11-2026: `~~halv` stod råt
  // i fladen, mens `~~hel~~` var pæn. Præcis samme halve-tilstand som `**`.
  const strikes = (synlig.match(/~~/g) ?? []).length
  if (strikes % 2 === 1) ud += '~~'

  // `$` (KaTeX inline-matematik) — men KUN når indholdet efter den åbne `$`
  // ser ud som matematik.
  //
  // En blind lukning er ikke sikker her, og det er målt: `Det koster $5` har
  // ét dollartegn, og en lukning ville gøre «5» til en formel midt i en
  // almindelig sætning. `Det koster $5 og $10` bliver allerede i dag parret
  // som matematik af remark-math (en eksisterende fejl, ikke indført her) —
  // så dollartegn i prosa er i forvejen et følsomt område, og vi må ikke
  // gøre det værre. Lukker derfor kun når der faktisk er en matematisk
  // markør i spillet: `\`, `^`, `_`, `{`, `}` eller `=`.
  const dollar = (synlig.match(/\$/g) ?? []).length
  if (dollar % 2 === 1) {
    const efter = synlig.slice(synlig.lastIndexOf('$') + 1)
    if (/[\\^_{}]|=/.test(efter)) ud += '$'
  }
  return ud
}
