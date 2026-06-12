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

// Tool-input nøgler der peger på en fil.
const TOOL_PATH_KEYS = ['target_path', 'file_path', 'path']

function isInternalPath(p: string): boolean {
  return FILE_ROOTS.some((root) => p.startsWith(`${root}/`))
}

/** Saml tool_use-blokkens input — fra `input` og evt. akkumuleret partialJson. */
function toolInput(block: Extract<ContentBlock, { type: 'tool_use' }>): Record<string, unknown> {
  let parsed: Record<string, unknown> = {}
  if (block.partialJson) {
    try {
      const j = JSON.parse(block.partialJson)
      if (j && typeof j === 'object') parsed = j as Record<string, unknown>
    } catch {
      /* ufuldstændig/ugyldig JSON — ignorér */
    }
  }
  return { ...parsed, ...(block.input ?? {}) }
}

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
    // 1) + 2) inline-artifacts fra modellens tekst.
    if (b.type === 'text') {
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
      continue
    }
    // 3) fil-referencer fra FAKTISKE tool-kald (ikke prosa) — binder panelet
    //    til filer Jarvis rent faktisk læste/skrev, så det ikke hober tilfældige
    //    stier op fra teksten.
    if (b.type === 'tool_use') {
      const input = toolInput(b)
      for (const key of TOOL_PATH_KEYS) {
        const val = input[key]
        if (typeof val !== 'string' || !isInternalPath(val)) continue
        if (!refs.some((r) => r.kind === 'file' && r.filePath === val)) {
          refs.push({ kind: 'file', title: val.split('/').pop() ?? val, filePath: val })
        }
      }
    }
  }
  return refs
}
