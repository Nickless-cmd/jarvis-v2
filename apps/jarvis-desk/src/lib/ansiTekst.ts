/**
 * Det terminal-agtige i et vaerktoejsresultat — foer farverne laegges paa.
 *
 * `ansiStykker` i `raekkeKroppe` oversaetter SGR (`\x1b[32m`) til spans. Alt
 * ANDET lader den staa, og saa staar det som skrald i teksten: `\x1b[2K`
 * bliver til «[2K» paa skaermen, og et `\r` bliver et usynligt kontroltegn
 * der skubber resten af linjen.
 *
 * **Maalt 30/9-2026 paa produktionsbasen (14 dage, ~81.000 beskeder):**
 *
 *     raa ESC              2
 *     escaped        9
 *     escaped \r          85
 *     escaped \t         120
 *
 * Det er derfor IKKE en terminal-emulator der bygges her. En kolonnebuffer
 * med tabulatorstop og dobbeltbredde ville vaere rigtig i en terminal og
 * forkert her: den koster en parser vi skal vedligeholde, for et moenster der
 * optraeder en haandfuld gange om ugen. De to ting der faktisk ses — ikke-SGR
 * sekvenser og `\r` — rettes, og resten staar noteret som ikke bygget.
 */

/** Alle CSI-sekvenser UNDTAGEN SGR (`m`). De styrer en markoer vi ikke har. */
// eslint-disable-next-line no-control-regex
const CSI_IKKE_SGR = /\x1b\[[0-9;?]*[A-LN-Za-ln-z]/g
/** OSC: `\x1b]0;titel\x07` — terminalens vinduestitel. Ikke indhold. */
// eslint-disable-next-line no-control-regex
const OSC = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g
/** Enkeltstaaende ESC-sekvenser uden parametre (`\x1bM`, `\x1b(B`). */
// eslint-disable-next-line no-control-regex
const ESC_ENKEL = /\x1b[()][0-9A-B]|\x1b[=>MD78]/g

/**
 * Hvad en terminal ville VISE for én linje med vognretur.
 *
 * `\r` flytter markoeren til kolonne 0 uden at slette. En progressbar skriver
 * `10%\r20%\r30%`, og en terminal viser «30%». Men overskriver et KORT
 * segment et laengere, staar halen af det lange tilbage: `hejsa\rhej` viser
 * «hejsa» med de tre foerste tegn erstattet — altsaa «hejsa», ikke «hej».
 * Det er dét der goer en naiv «tag sidste segment» forkert.
 */
export function anvendVognretur(linje: string): string {
  if (!linje.includes('\r')) return linje
  let ud = ''
  for (const del of linje.split('\r')) {
    ud = del.length >= ud.length ? del : del + ud.slice(del.length)
  }
  return ud
}

/**
 * Ryd det der ikke er farve, og lad vognreturen faa sin virkning.
 *
 * Raekkefoelgen betyder noget: sekvenserne fjernes FOER vognreturen, ellers
 * taeller en usynlig `\x1b[2K` med i segmentets laengde og lader en hale staa
 * der ikke findes.
 */
export function ryd(tekst: string): string {
  const uden = String(tekst ?? '')
    .replace(OSC, '')
    .replace(CSI_IKKE_SGR, '')
    .replace(ESC_ENKEL, '')
  if (!uden.includes('\r')) return uden
  // `\r\n` er en almindelig linjeslutning og maa ikke behandles som overskrivning.
  return uden.replace(/\r\n/g, '\n').split('\n').map(anvendVognretur).join('\n')
}
