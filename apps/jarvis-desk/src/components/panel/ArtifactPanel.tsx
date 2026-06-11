import { X, FileText, Code2, File } from 'lucide-react'
import type { Artifact } from '../../lib/artifacts'
import { MarkdownRenderer } from '../rich/MarkdownRenderer'
import { CodeBlock } from '../rich/CodeBlock'

const ICON = { markdown: FileText, code: Code2, file: File } as const

/** Panel-shell: header (ikon + titel + luk) + body renderet efter artifact.kind.
 *  'file' får async hentning i Task 10. */
export function ArtifactPanel({ artifact, onClose }: { artifact: Artifact; onClose: () => void }) {
  const Icon = ICON[artifact.kind] ?? File
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <Icon size={14} /> <span className="artifact-title">{artifact.title}</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body">
        {artifact.kind === 'markdown' && <MarkdownRenderer text={artifact.content ?? ''} streaming={false} />}
        {artifact.kind === 'code' && <CodeBlock code={artifact.content ?? ''} lang={artifact.language ?? 'text'} />}
      </div>
    </div>
  )
}
