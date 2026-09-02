/**
 * Minimal syntaksfarvning til kodeblokke.
 *
 * ChatGPT farver kode i deres app; vores blokke var ensfarvede. Et rigtigt
 * highlight-bibliotek (highlight.js/prism) er ~200 kB og trækker en HTML- eller
 * DOM-model med sig, som React Native alligevel ikke kan bruge direkte. Det vi
 * har brug for, er det ØJET fanger: strenge, kommentarer, tal og nøgleord.
 * Resten må gerne stå hvidt — det gør det også i referencen.
 *
 * Derfor en enkelt scanner frem for en parser. Den kan tage fejl i sære
 * tilfælde (fx en apostrof i en kommentar), og det er en accepteret pris:
 * en forkert farve på ét ord skader ikke, en manglende afhængighed på 200 kB
 * i en mobil-app gør.
 */

export type SpanKind = 'plain' | 'str' | 'com' | 'num' | 'kw'
export type Span = { text: string; kind: SpanKind }

const KEYWORDS = new Set([
  // fælles for de sprog der faktisk optræder i Jarvis' svar
  'const', 'let', 'var', 'function', 'return', 'if', 'else', 'for', 'while',
  'class', 'extends', 'new', 'this', 'import', 'from', 'export', 'default',
  'async', 'await', 'try', 'catch', 'finally', 'throw', 'typeof', 'instanceof',
  'interface', 'type', 'enum', 'public', 'private', 'protected', 'static',
  'def', 'elif', 'lambda', 'pass', 'raise', 'except', 'with', 'as', 'yield',
  'None', 'True', 'False', 'not', 'and', 'or', 'in', 'is', 'del', 'global',
  'null', 'undefined', 'true', 'false', 'void', 'break', 'continue', 'switch',
  'case', 'struct', 'impl', 'fn', 'pub', 'mut', 'use', 'match', 'echo', 'fi',
  'then', 'do', 'done', 'esac', 'local', 'select', 'where', 'insert', 'update'
])

// Rækkefølgen er betydningsbærende: kommentarer og strenge skal vinde over
// alt andet, ellers farves et nøgleord inde i en streng.
const SCANNER = new RegExp(
  [
    '(#[^\\n]*|//[^\\n]*|--[^\\n]*)',              // 1: linjekommentar
    '(/\\*[\\s\\S]*?\\*/)',                        // 2: blokkommentar
    '("""[\\s\\S]*?"""|\'\'\'[\\s\\S]*?\'\'\')',   // 3: python-docstring
    '(`(?:\\\\.|[^`\\\\])*`)',                     // 4: template-streng
    '("(?:\\\\.|[^"\\\\])*")',                     // 5: dobbelt
    "('(?:\\\\.|[^'\\\\])*')",                     // 6: enkelt
    '(\\b\\d[\\d_]*(?:\\.\\d+)?(?:[eE][+-]?\\d+)?\\b)', // 7: tal
    '([A-Za-z_$][A-Za-z0-9_$]*)'                   // 8: ord
  ].join('|'),
  'g'
)

export function highlight(code: string): Span[] {
  const out: Span[] = []
  const src = String(code ?? '')
  let last = 0

  const push = (text: string, kind: SpanKind) => {
    if (!text) return
    const prev = out[out.length - 1]
    // Slå naboer af samme slags sammen — færre <Text>-noder at tegne.
    if (prev && prev.kind === kind) prev.text += text
    else out.push({ text, kind })
  }

  SCANNER.lastIndex = 0
  let m: RegExpExecArray | null
  while ((m = SCANNER.exec(src)) !== null) {
    if (m.index > last) push(src.slice(last, m.index), 'plain')
    const [whole, lineCom, blockCom, doc, tmpl, dq, sq, num, word] = m
    if (lineCom || blockCom) push(whole, 'com')
    else if (doc || tmpl || dq || sq) push(whole, 'str')
    else if (num) push(whole, 'num')
    else if (word) push(whole, KEYWORDS.has(word) ? 'kw' : 'plain')
    else push(whole, 'plain')
    last = m.index + whole.length
  }
  if (last < src.length) push(src.slice(last), 'plain')
  return out
}
