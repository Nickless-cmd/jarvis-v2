/**
 * Fallback-syntaksfarvning når shiki ikke kan bruges.
 *
 * MÅLT 24/10-2026 (Bjørn: «med sprog tag, uden sprog tag er den vi har nu og
 * det er lort.. farver»): af 3.481 kodeblokke i chat_messages havde 41 %
 * (1.453) ingen sprog-tag og 4 % (161) et sprog shiki ikke kender (`cron` 95,
 * `jarvis-ui` 34, `|` 17, `conf`, `shell`, `git`). Begge grene ramte
 * `ChatCodeBlock`s rå-tekst-fallback: `if (!lang || !code) return` og
 * `.catch(() => null)`. Mobilen havde farve i ALLE blokke, fordi den bruger en
 * håndskrevet scanner (apps/mobile/src/lib/highlight.ts) frem for en parser —
 * derfor så telefonen rigtig ud og desk ikke.
 *
 * Denne fil er den scanner, portéret til desk, men med shiki's token-form som
 * udgangspunkt: hvert token bærer `--shiki-light`/`--shiki-dark` i `htmlStyle`,
 * præcis som shiki gør. Dermed kan ChatCodeBlock bruge ÉN render-sti uanset om
 * farven kom fra en grammatik eller herfra — og CSS-kaskaden
 * (`.jarvis-body .chat-shiki span { color: var(--shiki-dark) }`) virker uændret.
 *
 * Det er en scanner, ikke en parser. Den kan tage fejl i sære tilfælde (fx en
 * apostrof i en kommentar), og det er en accepteret pris — samme afvejning som
 * mobilens fil beskriver.
 */

export type FallbackToken = { content: string; htmlStyle: Record<string, string> }

/** Farverne er github-light/github-dark, de to temaer shiki er sat op med i
 *  chatCodeHighlight.ts. Kopieret frem for udledt, så fallback og grammatik
 *  farver identisk og en blok ikke skifter udseende når et sprogplun indlæses. */
const FARVE = {
  plain: { light: '#24292E', dark: '#E1E4E8' },
  kw: { light: '#D73A49', dark: '#F97583' },
  str: { light: '#032F62', dark: '#9ECBFF' },
  com: { light: '#6A737D', dark: '#6A737D' },
  num: { light: '#005CC5', dark: '#79B8FF' },
} as const

type Kind = keyof typeof FARVE

const KEYWORDS = new Set([
  'const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
  'class', 'extends', 'new', 'this', 'import', 'from', 'export', 'default',
  'async', 'await', 'try', 'catch', 'finally', 'throw', 'typeof', 'instanceof',
  'interface', 'type', 'enum', 'public', 'private', 'protected', 'static',
  'def', 'elif', 'lambda', 'pass', 'raise', 'except', 'with', 'as', 'yield',
  'None', 'True', 'False', 'not', 'and', 'or', 'in', 'is', 'del', 'global',
  'null', 'undefined', 'true', 'false', 'void', 'break', 'continue', 'switch',
  'case', 'struct', 'impl', 'fn', 'pub', 'mut', 'use', 'match', 'echo', 'fi',
  'then', 'do', 'done', 'esac', 'local', 'select', 'where', 'insert', 'update',
  'select', 'delete', 'create', 'table', 'sudo', 'cd', 'ls', 'cat', 'grep',
  'systemctl', 'git', 'curl', 'export', 'source', 'exit', 'test', 'fi',
])

/** Rækkefølgen er betydningsbærende: kommentarer og strenge skal vinde over alt
 *  andet, ellers farves et nøgleord inde i en streng. */
const SCANNER = new RegExp(
  [
    '(#[^\\n]*|//[^\\n]*|--[^\\n]*)', // 1: linjekommentar
    '(/\\*[\\s\\S]*?\\*/)', // 2: blokkommentar
    '("""[\\s\\S]*?"""|\'\'\'[\\s\\S]*?\'\'\')', // 3: python-docstring
    '(`(?:\\\\.|[^`\\\\])*`)', // 4: template-streng
    '("(?:\\\\.|[^"\\\\])*")', // 5: dobbelt
    "('(?:\\\\.|[^'\\\\])*')", // 6: enkelt
    '(\\b\\d[\\d_]*(?:\\.\\d+)?(?:[eE][+-]?\\d+)?\\b)', // 7: tal
    '([A-Za-z_$][A-Za-z0-9_$]*)', // 8: ord
  ].join('|'),
  'g',
)

function stil(kind: Kind): Record<string, string> {
  return { '--shiki-light': FARVE[kind].light, '--shiki-dark': FARVE[kind].dark }
}

/**
 * Tokenisér kode uden en grammatik. Returnerer linjer af tokens, samme form som
 * shiki's `codeToTokens`.
 */
export function fallbackTokens(code: string): FallbackToken[][] {
  const src = String(code ?? '')
  const linjer: FallbackToken[][] = [[]]
  const tryk = (tekst: string, kind: Kind) => {
    if (!tekst) return
    const linje = linjer[linjer.length - 1]
    if (!linje) return
    const forrige = linje[linje.length - 1]
    // Slå naboer af samme slags sammen — færre spans at tegne.
    if (forrige && forrige.htmlStyle['--shiki-dark'] === FARVE[kind].dark) {
      forrige.content += tekst
      return
    }
    linje.push({ content: tekst, htmlStyle: stil(kind) })
  }

  const skriv = (tekst: string, kind: Kind) => {
    if (!tekst) return
    // Ny linje = ny token-linje. Shiki gør det samme, og render-stien i
    // ChatCodeBlock indsætter '\n' mellem linjerne.
    const dele = tekst.split('\n')
    dele.forEach((del, i) => {
      if (i > 0) linjer.push([])
      tryk(del, kind)
    })
  }

  SCANNER.lastIndex = 0
  let sidst = 0
  let m: RegExpExecArray | null
  while ((m = SCANNER.exec(src)) !== null) {
    if (m.index > sidst) skriv(src.slice(sidst, m.index), 'plain')
    const [hel, linjeKom, blokKom, doc, tmpl, dq, sq, tal, ord] = m
    if (linjeKom || blokKom) skriv(hel, 'com')
    else if (doc || tmpl || dq || sq) skriv(hel, 'str')
    else if (tal) skriv(hel, 'num')
    else if (ord) skriv(hel, KEYWORDS.has(ord) ? 'kw' : 'plain')
    else skriv(hel, 'plain')
    sidst = m.index + hel.length
  }
  if (sidst < src.length) skriv(src.slice(sidst), 'plain')

  return linjer
}
