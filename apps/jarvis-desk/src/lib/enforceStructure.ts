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
 *  ender med `:` ELLER består af flere ord. Et enkelt kort bold-ord (`**fed**`)
 *  er emphasis, ikke en sektion, og skal forblive `<strong>`. */
function boldOnlyLineToHeader(text: string): string {
  return text.replace(
    /^[ \t]*\*\*([^*\n|]{1,80}?)\*\*[ \t]*$/gm,
    (match, header: string) => {
      const trimmed = header.trim()
      const headerLike = /:\s*$/.test(trimmed) || /\s/.test(trimmed)
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

/** Hovedfunktion: kør hele kæden over hver text-segment. */
export function enforceStructure(md: string): string {
  const segs = splitProtected(md)
  return segs
    .map((s) => {
      if (s.kind === 'fence') return s.body
      let t = s.body
      t = boldOnlyLineToHeader(t)
      t = boldPrefixInlineToHeader(t)
      t = flatEmDashLineToBullets(t)
      return t
    })
    .join('')
}
