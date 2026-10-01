// Spejl af apps/jarvis-desk/src/lib/enforceStructure.ts (1:1, 19/9-2026) — ret begge.
/** Strukturel håndhævelse af Jarvis' output-format.
 *
 *  Baggrund: Jarvis følger ikke konsekvent markdown-konventioner — han skriver
 *  hele lister eller tabeller på én linje. Vi reparerer eksplicitte
 *  Markdown-markører lige før render, også mens svaret streamer.
 *
 *  Vi lader eksisterende markdownblokke og fenced code (backticks/tilder)
 *  være urørte. Kun flad prosa er kandidat til strukturel reparation.
 */

/** Split tekst i prosa og beskyttede code-fences, også når den sidste er åben. */
function splitProtected(md: string): Array<{ kind: 'text' | 'fence'; body: string }> {
  const out: Array<{ kind: 'text' | 'fence'; body: string }> = []
  let body = ''
  let fence: { marker: string; length: number } | null = null
  const flush = (kind: 'text' | 'fence') => {
    if (body) out.push({ kind, body })
    body = ''
  }
  for (const line of md.match(/[^\n]*(?:\n|$)/g)?.filter(Boolean) ?? []) {
    const content = line.replace(/\r?\n$/, '')
    if (!fence) {
      const opening = /^ {0,3}(`{3,}|~{3,})/.exec(content)
      if (opening) {
        flush('text')
        fence = { marker: opening[1]![0]!, length: opening[1]!.length }
      }
      body += line
    } else {
      body += line
      const closing = /^ {0,3}(`{3,}|~{3,})[ \t]*$/.exec(content)
      if (closing && closing[1]![0] === fence.marker && closing[1]!.length >= fence.length) {
        flush('fence')
        fence = null
      }
    }
  }
  flush(fence ? 'fence' : 'text')
  return out
}

/** Eksisterende markdown-blokke er ikke kandidater til reparation af flad prosa. */
function isStructuredLine(line: string): boolean {
  return /^[ \t]/.test(line) || line.includes('|') || /^(?:[-*+](?:[ \t]|$)|\d{1,9}[.)][ \t]|>|#{1,6}[ \t])/.test(line)
}

function mapPlainLines(text: string, transform: (line: string) => string): string {
  return text.split('\n').map((line) => isStructuredLine(line) ? line : transform(line)).join('\n')
}

/** Jarvis skriver undertiden `**1 · Titel**` i stedet for `1. **Titel**`.
 * Kun linjestart tæller; citater og fed tekst midt i prosa er ikke lister. */
function boldNumberToList(text: string): string {
  return text.replace(
    /^([ \t]{0,3})\*\*(\d{1,3})[ \t]*·[ \t]+([^*\n]+)\*\*/gm,
    (_match, indent: string, number: string, title: string) => `${indent}${number}. **${title}**`,
  )
}

// ── Inline-markør-rekonstruktion (spejler core/services/markdown_structure.py) ──
// Jarvis emitterer ~50% af svar UDEN newlines: hele lister og afsnit på én linje
// med ` - ` inline. Fede etiketter er Markdown og bevares. Backend-normalizeren
// retter gemt tekst og kanaltekst, men
// klienten akkumulerer streaming-deltas live og reconciler ikke — så vi spejler
// samme logik her, så LIVE-visningen også bliver struktureret.

const INLINE_STATEMENT = /(?<=\S)[ \t]+(\*\*(?=[^*\n]*\s)[^*\n]{1,160}?[.!?]\*\*)[ \t]+(?=\S)/g
const INLINE_BULLET = /(?<=\S)[ \t]-[ \t](?=\S)/g

/** Flerords-`**sætning.**` midt i en linje → eget afsnit (ikke kort emphasis). */
function inlineStatementToParagraph(text: string): string {
  return text.replace(INLINE_STATEMENT, '\n\n$1\n\n')
}

/** Inline ATX-header `... : ## Header` midt i en linje → headeren på egen blok.
 *  2-6 hashes (undgår `C#`, `issue #5`) + content før + content efter. */
const INLINE_ATX = /(?<=\S)[ \t]+(#{2,6}[ \t]+)(?=\S)/g
function inlineAtxToBlock(text: string): string {
  return text.replace(INLINE_ATX, '\n\n$1')
}

function isBulletLine(line: string): boolean {
  const s = line.trimStart()
  return s.startsWith('- ') || /^\d+\.[ \t]/.test(s)
}

/** Indsæt blank linje før første bullet i en liste der følger prosa. */
function blankBeforeLists(text: string): string {
  const out: string[] = []
  for (const line of text.split('\n')) {
    if (isBulletLine(line) && out.length) {
      const prev = out[out.length - 1] as string
      if (prev.trim() && !isBulletLine(prev)) out.push('')
    }
    out.push(line)
  }
  return out.join('\n')
}

/** ` - ` inline bullets → liste (kun ægte liste: 2+ markører). */
function inlineBulletsToList(text: string): string {
  if ((text.match(INLINE_BULLET) || []).length < 2) return text
  return blankBeforeLists(text.replace(INLINE_BULLET, '\n- '))
}

/** En tabel-celle der KUN er bindestreger/koloner/whitespace = separator-celle. */
const SEP_CELL = /^\s*:?-{1,}:?\s*$/

/** Split en `|`-region i celler; drop ydre tomme (før første/efter sidste pipe). */
function splitCells(region: string): string[] {
  const parts = region.split('|')
  if (parts.length && (parts[0] as string).trim() === '') parts.shift()
  if (parts.length && (parts[parts.length - 1] as string).trim() === '') parts.pop()
  return parts
}

/** Hel tabel mast sammen på én linje → rigtige rækker. null hvis ikke crammed. */
function reflowLineTable(line: string): string | null {
  const first = line.indexOf('|')
  const last = line.lastIndexOf('|')
  if (first < 0 || last <= first) return null
  const prefix = line.slice(0, first)
  const region = line.slice(first, last + 1)
  const suffix = line.slice(last + 1)
  const cells = splitCells(region)
  if (cells.length < 4) return null
  // Find første run af >=2 sammenhængende separator-celler = kolonne-antal.
  let sepStart = -1
  let sepLen = 0
  let i = 0
  while (i < cells.length) {
    if (SEP_CELL.test(cells[i] as string)) {
      let j = i
      while (j < cells.length && SEP_CELL.test(cells[j] as string)) j++
      if (j - i >= 2) { sepStart = i; sepLen = j - i; break }
      i = j
    } else i++
  }
  if (sepStart < 1) return null // header skal være FØR separator på samme linje
  const n = sepLen
  let header = cells.slice(0, sepStart).map((c) => c.trim())
  let data = cells.slice(sepStart + sepLen).map((c) => c.trim())
  // Hele rækker uden linjeskift — `| a | b | | c | d |` — giver en tom celle
  // mellem rækkerne. Spejl af `markdown_structure.py` (19/9-2026); kun når
  // mønstret holder hele vejen.
  if (header.length === n + 1 && header[n] === '') {
    header = header.slice(0, n)
    if (data[0] === '') data = data.slice(1)
    let alle = true
    for (let k = n; k < data.length; k += n + 1) if (data[k] !== '') { alle = false; break }
    if (alle) data = data.filter((_, k) => k % (n + 1) !== n)
  }
  const rows = [`| ${header.join(' | ')} |`, `| ${Array(n).fill('---').join(' | ')} |`]
  for (let k = 0; k < data.length; k += n) rows.push(`| ${data.slice(k, k + n).join(' | ')} |`)
  const out: string[] = []
  if (prefix.trim()) out.push(prefix.replace(/\s+$/, ''))
  out.push('', rows.join('\n'), '')
  if (suffix.trim()) out.push(suffix.replace(/^\s+/, ''))
  return out.join('\n')
}

/** Genskab tabeller hvis hele rækken er mast sammen på én linje. */
function reflowCrammedTables(text: string): string {
  if (!text.includes('|')) return text
  return text
    .split('\n')
    .map((line) => ((line.match(/\|/g) || []).length >= 4 ? reflowLineTable(line) ?? line : line))
    .join('\n')
}

/** Hovedfunktion: kør hele kæden over hver text-segment. */
export function enforceStructure(md: string): string {
  const segs = splitProtected(md)
  return segs
    .map((s) => {
      if (s.kind === 'fence') return s.body
      let t = s.body
      const codeSpans: string[] = []
      t = t.replace(/(?<!`)(`{1,2})(?!`)[\s\S]*?\1(?!`)/g, (code) => {
        codeSpans.push(code)
        return `\0${codeSpans.length - 1}\0`
      })
      // Crammed tabeller FØRST → celler på egne linjer før resten af kæden.
      t = reflowCrammedTables(t)
      t = boldNumberToList(t)
      // Inline → blok FØRST, så de linje-baserede regler ser rigtige linjer.
      t = mapPlainLines(t, (line) => inlineBulletsToList(inlineAtxToBlock(inlineStatementToParagraph(line))))
      // Bevar modellens fed tekst og em dash som skrevet. Kun eksplicitte Markdown-markører repareres.
      return t.replace(/\n{3,}/g, '\n\n')
        .replace(/\0(\d+)\0/g, (_, index: string) => codeSpans[Number(index)] ?? '')
    })
    .join('')
}
