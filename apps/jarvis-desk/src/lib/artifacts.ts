import type { ContentBlock } from './sseProtocol'

export type ArtifactKind = 'markdown' | 'code' | 'file' // v2: 'mermaid' | 'html'

export interface Artifact {
  kind: ArtifactKind
  title: string
  language?: string
  content?: string // inline (markdown/code)
  filePath?: string // for 'file'
}

/** En detekteret reference, klar til at blive til et Artifact ved klik. */
export type ArtifactRef = Artifact

const CODE_MIN_LINES = 15
const MD_MIN_LINES = 40

// Interne sti-rødder vi tør linke (matcher backend path-jail).
const FILE_ROOTS = ['docs', 'workspace', 'core', 'apps', 'scripts']
const FILE_RE = new RegExp(
  `(?<![\\w/])((?:${FILE_ROOTS.join('|')})/[\\w./-]+\\.[a-z]{1,5})`,
  'g',
)

function fencedBlocks(text: string): Array<{ lang: string; body: string }> {
  const out: Array<{ lang: string; body: string }> = []
  const re = /```([\w-]*)\n([\s\S]*?)```/g
  let m: RegExpExecArray | null
  while ((m = re.exec(text)) !== null) out.push({ lang: m[1] || '', body: m[2] ?? '' })
  return out
}

function headerCount(text: string): number {
  return (text.match(/^#{1,6}\s/gm) ?? []).length
}

export function detectArtifacts(blocks: ContentBlock[]): ArtifactRef[] {
  const refs: ArtifactRef[] = []
  for (const b of blocks) {
    if (b.type !== 'text') continue
    // 1) fenced kodeblokke
    for (const { lang, body } of fencedBlocks(b.text)) {
      if (body.split('\n').length >= CODE_MIN_LINES) {
        refs.push({
          kind: 'code',
          title: lang ? `${lang}-kode` : 'Kode',
          language: lang || 'text',
          content: body,
        })
      }
    }
    // 2) langt markdown-dok (linjer + headers)
    const lines = b.text.split('\n').length
    if (lines >= MD_MIN_LINES && headerCount(b.text) >= 2) {
      const title = (b.text.match(/^#\s+(.+)$/m)?.[1] ?? 'Dokument').trim()
      refs.push({ kind: 'markdown', title, content: b.text })
    }
    // 3) interne fil-referencer
    for (const m of b.text.matchAll(FILE_RE)) {
      const filePath = m[1]
      if (!filePath) continue
      if (!refs.some((r) => r.kind === 'file' && r.filePath === filePath)) {
        refs.push({ kind: 'file', title: filePath.split('/').pop() ?? filePath, filePath })
      }
    }
  }
  return refs
}
