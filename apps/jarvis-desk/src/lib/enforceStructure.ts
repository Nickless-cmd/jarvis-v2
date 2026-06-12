/** Strukturel håndhævelse af Jarvis' output-format.
 *
 *  Baggrund: Jarvis følger ikke konsekvent markdown-konventioner — han skriver
 *  ofte `**Header**` på egen linje i stedet for `## Header`. Frem for at bede
 *  ham om at gøre det rigtigt transformerer vi hans tekst *strukturelt* lige
 *  før render. Det fanger 80% af tilfældene uden at røre hans skrivestil eller
 *  backend.
 *
 *  Sikkerhed: vi springer alt indhold inde i code-fences (```...```) over,
 *  og vi rører ALDRIG indhold inde i list-items (bullets/numbered) — der bruger
 *  Jarvis em-dash korrekt og det rendres pænt som det er.
 */

/** Splittet tekst i segmenter: enten almindelig tekst (skal transformeres) eller
 *  beskyttet (code-fence, der skal lades helt i fred). */
function splitProtected(md: string): Array<{ kind: 'text' | 'fence'; body: string }> {
  const out: Array<{ kind: 'text' | 'fence'; body: string }> = []
  const re = /```[\s\S]*?```/g
  let last = 0
  let m: RegExpExecArray | null
  while ((m = re.exec(md)) !== null) {
    if (m.index > last) out.push({ kind: 'text', body: md.slice(last, m.index) })
    out.push({ kind: 'fence', body: m[0] })
    last = m.index + m[0].length
  }
  if (last < md.length) out.push({ kind: 'text', body: md.slice(last) })
  return out
}

/** `**Header**` eller `**Header:**` på egen linje → `## Header`.
 *  Kun når linjen kun indeholder bold-spannen (intet andet tekst udenom).
 *  Header-teksten må ikke selv indeholde `*`, newline, eller pipe (tabel).
 *
 *  Konservativ: vi promoverer KUN hvis linjen ligner en header — dvs. enten
 *  ender med `:` ELLER er flere ord UDEN afsluttende sætningstegn. Et enkelt
 *  kort bold-ord (`**fed**`) er emphasis; en flerords-bold der ender på `.!?`
 *  (`**Det er chat.**`) er en udsagn-sætning — begge skal forblive `<strong>`,
 *  ikke blive til en `<h2>`. */
function boldOnlyLineToHeader(text: string): string {
  return text.replace(
    /^[ \t]*\*\*([^*\n|]{1,80}?)\*\*[ \t]*$/gm,
    (match, header: string) => {
      const trimmed = header.trim()
      const endsColon = /:\s*$/.test(trimmed)
      const endsSentence = /[.!?]\s*$/.test(trimmed)
      const headerLike = endsColon || (/\s/.test(trimmed) && !endsSentence)
      if (!headerLike) return match
      const clean = trimmed.replace(/:\s*$/, '').trim()
      return `## ${clean}`
    },
  )
}

/** `**Header:**` efterfulgt af tekst på samme linje → `## Header\n\ntekst`.
 *  Konservativ: kræver Capital-start på header og minst 8 chars body for at
 *  undgå at slå korte bold-inline-spans i stykker. */
function boldPrefixInlineToHeader(text: string): string {
  return text.replace(
    /^[ \t]*\*\*([A-ZÆØÅ][^*\n]{1,60}?):\*\*[ \t]+([^\n]{8,}?)$/gm,
    (_match, header: string, body: string) => `## ${header.trim()}\n\n${body.trim()}`,
  )
}

/** Flad em-dash-separeret linje med 3+ separationer → bullet-liste.
 *
 *  Eksempel input:
 *    Vi har flere lag — API kører — Session er portabel — Auth findes — WS klar
 *
 *  Detekteres KUN når:
 *  - Linjen IKKE starter med bullet/numbered marker (-, *, 1.)
 *  - Linjen IKKE er inde i en tabel (indeholder ikke `|`)
 *  - Mindst 3 ` — ` separationer (em-dash med mellemrum)
 *  - Hvert segment er kort (< 80 chars) — så det ligner et list-item
 *
 *  Konservativ: vi rører IKKE almindelig prosa hvor em-dash bruges som tankestreg.
 */
function flatEmDashLineToBullets(text: string): string {
  const lines = text.split('\n')
  const out: string[] = []
  for (const line of lines) {
    const trimmed = line.trimStart()
    // Spring over hvis det er bullet/numbered/table/header/quote allerede
    if (/^([-*+]|\d+\.|#|>|\|)/.test(trimmed)) {
      out.push(line)
      continue
    }
    // Spring over hvis linjen er kort eller mangler em-dash
    if (trimmed.length < 30 || !trimmed.includes(' — ')) {
      out.push(line)
      continue
    }
    const parts = trimmed.split(' — ')
    if (parts.length < 4) {
      // 4 parts = 3 separators
      out.push(line)
      continue
    }
    // Tjek at hvert segment er kort (list-agtigt)
    if (parts.some((p) => p.length > 80)) {
      out.push(line)
      continue
    }
    // Konverter: første del bliver intro hvis den ender med `:`, ellers første bullet
    if (parts[0]?.endsWith(':')) {
      out.push(parts[0])
      for (const p of parts.slice(1)) out.push(`- ${p.trim()}`)
    } else {
      for (const p of parts) out.push(`- ${p.trim()}`)
    }
  }
  return out.join('\n')
}

// ── Inline-markør-rekonstruktion (spejler core/services/markdown_structure.py) ──
// Jarvis emitterer ~50% af svar UDEN newlines: hele lister og afsnit på én linje
// med ` - ` og `**X:**` inline. Backend-normalizer retter gemt/kanal-tekst, men
// klienten akkumulerer streaming-deltas live og reconciler ikke — så vi spejler
// samme logik her, så LIVE-visningen også bliver struktureret.

const INLINE_HEADER = /(?<=\S)[ \t]+(\*\*[^*\n]{1,80}?:\*\*)[ \t]+(?=\S)/g
const INLINE_STATEMENT = /(?<=\S)[ \t]+(\*\*(?=[^*\n]*\s)[^*\n]{1,160}?[.!?]\*\*)[ \t]+(?=\S)/g
const INLINE_BULLET = /(?<=\S)[ \t]-[ \t](?=\S)/g

/** `**Header:**` midt i en linje → egen blok. */
function inlineHeaderToBlock(text: string): string {
  return text.replace(INLINE_HEADER, '\n\n$1\n\n')
}

/** Flerords-`**sætning.**` midt i en linje → eget afsnit (ikke kort emphasis). */
function inlineStatementToParagraph(text: string): string {
  return text.replace(INLINE_STATEMENT, '\n\n$1\n\n')
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

/** Hovedfunktion: kør hele kæden over hver text-segment. */
export function enforceStructure(md: string): string {
  const segs = splitProtected(md)
  return segs
    .map((s) => {
      if (s.kind === 'fence') return s.body
      let t = s.body
      // Inline → blok FØRST, så de linje-baserede regler ser rigtige linjer.
      t = inlineHeaderToBlock(t)
      t = inlineStatementToParagraph(t)
      t = inlineBulletsToList(t)
      t = boldOnlyLineToHeader(t)
      t = boldPrefixInlineToHeader(t)
      t = flatEmDashLineToBullets(t)
      return t.replace(/\n{3,}/g, '\n\n')
    })
    .join('')
}
