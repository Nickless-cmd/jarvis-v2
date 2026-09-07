/** Hvad kan vi vise af en fil — og hvad skal overlades til systemet?
 *
 *  Codex lavede billed-previews. Resten af listen (PDF, tekst, kode) manglede,
 *  og forskellen mellem dem er ikke kosmetisk: en tekstfil kan vi vise INDE i
 *  appen, mens en PDF kraever en fremviser. At proeve at rendere en PDF selv
 *  ville vaere en daarlig kopi af noget telefonen allerede kan.
 *
 *  Derfor tre udfald:
 *    inline   vi viser indholdet selv (tekst, kode, markdown, json…)
 *    billede  vi viser det som billede (Codex' vej)
 *    system   vi aabner den i telefonens egen fremviser (PDF, kontor, zip…)
 */

export type PreviewSlags = 'billede' | 'inline' | 'system'

export interface PreviewPlan {
  slags: PreviewSlags
  /** Sprog til syntaks-farvning når slags === 'inline'. "" = almindelig tekst. */
  sprog: string
  /** Menneske-laesbar type til etiketten under filnavnet. */
  etiket: string
}

// Endelse → (sprog, etiket). Sproget bruges af CodeBlock; tom = ren tekst.
const KODE: Record<string, [string, string]> = {
  ts: ['typescript', 'TypeScript'], tsx: ['tsx', 'TypeScript'],
  js: ['javascript', 'JavaScript'], jsx: ['jsx', 'JavaScript'],
  py: ['python', 'Python'], rb: ['ruby', 'Ruby'], go: ['go', 'Go'],
  rs: ['rust', 'Rust'], java: ['java', 'Java'], kt: ['kotlin', 'Kotlin'],
  swift: ['swift', 'Swift'], c: ['c', 'C'], h: ['c', 'C'],
  cpp: ['cpp', 'C++'], cs: ['csharp', 'C#'], php: ['php', 'PHP'],
  sh: ['bash', 'Shell'], bash: ['bash', 'Shell'], zsh: ['bash', 'Shell'],
  sql: ['sql', 'SQL'], html: ['html', 'HTML'], css: ['css', 'CSS'],
  json: ['json', 'JSON'], yaml: ['yaml', 'YAML'], yml: ['yaml', 'YAML'],
  toml: ['toml', 'TOML'], xml: ['xml', 'XML'], ini: ['ini', 'Config'],
  gradle: ['groovy', 'Gradle'], dockerfile: ['dockerfile', 'Dockerfile'],
}
const TEKST: Record<string, string> = {
  txt: 'Tekst', md: 'Markdown', markdown: 'Markdown', log: 'Log',
  csv: 'CSV', tsv: 'TSV', env: 'Config', conf: 'Config', cfg: 'Config',
}
const SYSTEM: Record<string, string> = {
  pdf: 'PDF', doc: 'Word', docx: 'Word', xls: 'Excel', xlsx: 'Excel',
  ppt: 'PowerPoint', pptx: 'PowerPoint', zip: 'Arkiv', tar: 'Arkiv',
  gz: 'Arkiv', apk: 'App', mp4: 'Video', mov: 'Video', mp3: 'Lyd',
  wav: 'Lyd', m4a: 'Lyd',
}

/** Filer over dette vises ikke inline — man laeser ikke en megabyte i en boble. */
export const INLINE_MAKS_BYTES = 256 * 1024

function endelse(filnavn: string): string {
  const n = String(filnavn || '').toLowerCase()
  if (n.endsWith('dockerfile') || n === 'dockerfile') return 'dockerfile'
  const i = n.lastIndexOf('.')
  return i > 0 ? n.slice(i + 1) : ''
}

export function planlaegPreview(
  filnavn: string, mime = '', stoerrelseBytes = 0,
): PreviewPlan {
  const m = String(mime || '').toLowerCase()
  const e = endelse(filnavn)

  if (m.startsWith('image/') || ['png', 'jpg', 'jpeg', 'gif', 'webp', 'bmp', 'heic'].includes(e)) {
    return { slags: 'billede', sprog: '', etiket: 'Billede' }
  }
  if (m === 'application/pdf' || SYSTEM[e]) {
    return { slags: 'system', sprog: '', etiket: SYSTEM[e] || 'Fil' }
  }
  // For stor til at vise inline — men vi ved stadig hvad den er.
  const forStor = stoerrelseBytes > INLINE_MAKS_BYTES
  if (KODE[e]) {
    const [sprog, etiket] = KODE[e]
    return forStor
      ? { slags: 'system', sprog: '', etiket }
      : { slags: 'inline', sprog, etiket }
  }
  if (TEKST[e] || m.startsWith('text/')) {
    const etiket = TEKST[e] || 'Tekst'
    return forStor
      ? { slags: 'system', sprog: '', etiket }
      : { slags: 'inline', sprog: '', etiket }
  }
  return { slags: 'system', sprog: '', etiket: e ? e.toUpperCase() : 'Fil' }
}
