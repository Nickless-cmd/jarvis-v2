/**
 * Det terminal-agtige i et værktøjsresultat — før farverne lægges på.
 *
 * Porteret fra desks `lib/ansiTekst.ts` (spec punkt 6, 30/9-2026), af samme
 * grund: `ls --color`, `git diff --color` og `grep --color` skriver
 * SGR-sekvenser (`\x1b[32m`) ind i stdout — og alt ANDET de skriver stod som
 * skrald midt i teksten. `\x1b[2K` blev til «[2K» på skærmen, og et `\r` blev
 * et usynligt kontroltegn der skubbede resten af linjen.
 *
 * ## Målt, ikke gættet
 *
 * Desk målte mønsteret på produktionsbasen (14 dage, ~81.000 beskeder):
 *
 *     rå ESC              2
 *     escaped        9
 *     escaped \r          85
 *     escaped \t         120
 *
 * Det er derfor IKKE en terminal-emulator der bygges her. En kolonnebuffer
 * med tabulatorstop og dobbeltbredde ville være rigtig i en terminal og
 * forkert her: den koster en parser vi skal vedligeholde, for et mønster der
 * optræder en håndfuld gange om ugen. De to ting der faktisk ses — ikke-SGR
 * sekvenser og `\r` — rettes, og resten står noteret som ikke bygget.
 */

/** Alle CSI-sekvenser UNDTAGEN SGR (`m`). De styrer en markør vi ikke har. */
// eslint-disable-next-line no-control-regex
const CSI_IKKE_SGR = /\x1b\[[0-9;?]*[A-LN-Za-ln-z]/g
/** OSC: `\x1b]0;titel\x07` — terminalens vinduestitel. Ikke indhold. */
// eslint-disable-next-line no-control-regex
const OSC = /\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)/g
/** Enkeltstående ESC-sekvenser uden parametre (`\x1bM`, `\x1b(B`). */
// eslint-disable-next-line no-control-regex
const ESC_ENKEL = /\x1b[()][0-9A-B]|\x1b[=>MD78]/g

/**
 * Hvad en terminal ville VISE for én linje med vognretur.
 *
 * `\r` flytter markøren til kolonne 0 uden at slette. En progressbar skriver
 * `10%\r20%\r30%`, og en terminal viser «30%». Men overskriver et KORT
 * segment et længere, står halen af det lange tilbage: `hejsa\rhej` viser
 * «hejsa» med de tre første tegn erstattet — altså «hejsa», ikke «hej». Det er
 * dét der gør en naiv «tag sidste segment» forkert.
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
 * Ryd det der ikke er farve, og lad vognreturen få sin virkning.
 *
 * Rækkefølgen betyder noget: sekvenserne fjernes FØR vognreturen, ellers
 * tæller en usynlig `\x1b[2K` med i segmentets længde og lader en hale stå der
 * ikke findes.
 */
export function ryd(tekst: string): string {
  const uden = String(tekst ?? '')
    .replace(OSC, '')
    .replace(CSI_IKKE_SGR, '')
    .replace(ESC_ENKEL, '')
  if (!uden.includes('\r')) return uden
  // `\r\n` er en almindelig linjeslutning og må ikke behandles som overskrivning.
  return uden.replace(/\r\n/g, '\n').split('\n').map(anvendVognretur).join('\n')
}

/* ══ SGR: farvekoderne ══════════════════════════════════════════════════ */

export interface AnsiStil {
  /** 0-15: indeks i `ANSI_FARVER`. `undefined` = arv. */
  fg?: number
  /** Sande 24-bit farver (`38;2;r;g;b`). Vinder over `fg`. */
  rgb?: string
  bold?: boolean
  dim?: boolean
}

export const ANSI_TOM: AnsiStil = {}

/**
 * Desk's palet, ordret (`raekkevisning.css:426-431`, dark mode).
 *
 * Den er One Dark og ikke xterm-grøn: den skal kunne læses oveni appens egen
 * flade, ikke se ud som en terminal fra 1994. Vi oversætter koderne i stedet
 * for at fjerne dem — farven ER information, den er hele grunden til at
 * værktøjet skrev den.
 */
export const ANSI_FARVER = [
  '#4a5058', '#e06c75', '#98c379', '#e5c07b',
  '#61afef', '#c678dd', '#56b6c2', '#abb2bf',
  '#6b7280', '#ef7e6b', '#b6e3a0', '#f0d197',
  '#82c4f5', '#d99ee8', '#7fd0d9', '#ffffff',
]

// ESC er et kontroltegn — det ER definitionen af en ANSI-sekvens.
// eslint-disable-next-line no-control-regex
const ANSI_RE = /\x1b\[([0-9;]*)m/g

function anvendSgr(koder: number[], t: AnsiStil): AnsiStil {
  const n: AnsiStil = { ...t }
  for (let i = 0; i < koder.length; i++) {
    const k = koder[i] ?? 0
    if (k === 0) { n.fg = undefined; n.rgb = undefined; n.bold = false; n.dim = false }
    else if (k === 1) n.bold = true
    else if (k === 2) n.dim = true
    else if (k === 22) { n.bold = false; n.dim = false }
    else if (k === 39) { n.fg = undefined; n.rgb = undefined }
    else if (k >= 30 && k <= 37) { n.fg = k - 30; n.rgb = undefined }
    else if (k >= 90 && k <= 97) { n.fg = k - 90 + 8; n.rgb = undefined }
    else if (k === 38 && koder[i + 1] === 2) {
      n.rgb = `rgb(${koder[i + 2] ?? 0}, ${koder[i + 3] ?? 0}, ${koder[i + 4] ?? 0})`
      n.fg = undefined
      i += 4
    }
  }
  return n
}

/**
 * Del teksten i stykker med hver sin stil.
 *
 * Vi bygger `<Text>`-noder i React Native, ikke HTML. Et fjendtligt
 * værktøjsresultat kan derfor ikke smugle markup ind — der er ingen
 * `dangerouslySetInnerHTML` i denne vej.
 *
 * Vi understøtter de 16 standardfarver samt fed/dæmpet. 256-farver og
 * baggrund falder tilbage til arvet farve — de ville kræve en terminal vi ikke
 * er, og `git`, `ls` og `grep` bruger dem ikke i praksis.
 */
export function ansiStykker(tekst: string): { t: string; s: AnsiStil }[] {
  const ud: { t: string; s: AnsiStil }[] = []
  let s = ANSI_TOM
  let sidst = 0
  ANSI_RE.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = ANSI_RE.exec(tekst)) !== null) {
    if (m.index > sidst) ud.push({ t: tekst.slice(sidst, m.index), s })
    const koder = (m[1] || '').split(';').map((x) => Number(x) || 0)
    s = koder.length === 1 && koder[0] === 0 ? ANSI_TOM : anvendSgr(koder, s)
    sidst = m.index + m[0].length
  }
  if (sidst < tekst.length) ud.push({ t: tekst.slice(sidst), s })
  return ud
}
