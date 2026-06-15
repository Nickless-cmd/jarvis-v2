import { useEffect, useState } from 'react'
import { X, FileText, Code2, File } from 'lucide-react'
import type { Artifact } from '../../lib/artifacts'
import { getFile, type ApiConfig } from '../../lib/api'
import { MarkdownRenderer } from '../rich/MarkdownRenderer'
import { CodeBlock } from '../rich/CodeBlock'

const ICON = { markdown: FileText, code: Code2, file: File } as const

/** Panel-shell: header (ikon + titel + luk) + body renderet efter artifact.kind.
 *  Tomt artifact (åbnet via header-toggle) → placeholder. 'file' hentes async
 *  via GET /chat/file og renderes som markdown eller kode efter sprog. */
export function ArtifactPanel({
  artifact,
  onClose,
  config,
}: {
  artifact: Artifact | null
  onClose: () => void
  config?: ApiConfig
}) {
  const [fileData, setFileData] = useState<{ content: string; language: string } | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    setFileData(null)
    setError(null)
    if (artifact?.kind === 'file' && artifact.filePath && config) {
      // Artifact-stier er repo-relative (specs/kode fra Jarvis) → 'repo'-root.
      getFile(config, 'repo', artifact.filePath)
        .then((d) => setFileData({ content: d.content, language: d.language }))
        .catch(() => setError('Kunne ikke hente filen'))
    }
  }, [artifact, config])

  const Icon = artifact ? (ICON[artifact.kind] ?? File) : File
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <Icon size={14} /> <span className="artifact-title">{artifact?.title ?? 'Panel'}</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body">
        {!artifact && (
          <div className="artifact-empty">
            Intet at vise endnu.<br />
            Jarvis' specs, kode og filer åbner her — klik "Åbn ↗" under et svar.
          </div>
        )}
        {artifact?.kind === 'markdown' && <MarkdownRenderer text={artifact.content ?? ''} streaming={false} />}
        {artifact?.kind === 'code' && <CodeBlock code={artifact.content ?? ''} lang={artifact.language ?? 'text'} />}
        {artifact?.kind === 'file' && error && <div className="artifact-error">{error}</div>}
        {artifact?.kind === 'file' && !error && !fileData && <div className="artifact-loading">Henter…</div>}
        {artifact?.kind === 'file' && fileData && (
          fileData.language === 'markdown'
            ? <MarkdownRenderer text={fileData.content} streaming={false} />
            : <CodeBlock code={fileData.content} lang={fileData.language} />
        )}
      </div>
    </div>
  )
}
