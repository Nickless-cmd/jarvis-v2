import { useState } from 'react'
import { ChevronRight, Link as LinkIcon } from 'lucide-react'
import { sourcesForTool, type SourceEvidence, type ToolEvidence } from '../../lib/environmentEvidence'
import { lookupTool } from '../../lib/toolRegistry'

const RESULT_LIMIT = 12_000

function formatted(value: unknown): string {
  if (typeof value !== 'string') return JSON.stringify(value, null, 2)
  try {
    return JSON.stringify(JSON.parse(value), null, 2)
  } catch {
    return value
  }
}

function statusLabel(status: ToolEvidence['status']): string {
  if (status === 'error') return 'Fejlet'
  if (status === 'running') return 'Kører'
  return 'Færdig'
}

export function ToolInspector({
  tool,
  onOpenSource,
}: {
  tool: ToolEvidence
  onOpenSource: (source: SourceEvidence) => void
}) {
  const [expanded, setExpanded] = useState(false)
  const meta = lookupTool(tool.name)
  const sources = sourcesForTool(tool)
  const rawResult = tool.result ?? ''
  const result = formatted(expanded || rawResult.length <= RESULT_LIMIT
    ? rawResult
    : rawResult.slice(0, RESULT_LIMIT))

  return (
    <div className="inspector-body tool-inspector">
      <section className="inspector-section">
        <div className="inspector-kicker">Tool</div>
        <div className="tool-inspector-title">{meta.label}</div>
        <dl className="inspector-facts">
          <div><dt>Navn</dt><dd className="inspector-mono">{tool.name}</dd></div>
          <div><dt>ID</dt><dd className="inspector-mono">{tool.id}</dd></div>
          <div><dt>Status</dt><dd className={`tool-status is-${tool.status}`}>{statusLabel(tool.status)}</dd></div>
        </dl>
      </section>

      <section className="inspector-section">
        <div className="inspector-kicker">Input</div>
        <pre className="inspector-pre">{formatted(tool.input)}</pre>
      </section>

      <section className="inspector-section">
        <div className="inspector-kicker">Resultat</div>
        {rawResult
          ? <pre className="inspector-pre">{result}</pre>
          : <div className="inspector-empty">{tool.status === 'running' ? 'Kører stadig…' : 'Intet resultat gemt'}</div>}
        {rawResult.length > RESULT_LIMIT && !expanded && (
          <button type="button" className="inspector-secondary" onClick={() => setExpanded(true)}>
            Vis hele resultatet
          </button>
        )}
      </section>

      {sources.length > 0 && (
        <section className="inspector-section">
          <div className="inspector-kicker">Kilder fra dette kald</div>
          <div className="inspector-link-list">
            {sources.map((source) => (
              <button type="button" key={source.url} onClick={() => onOpenSource(source)}>
                <LinkIcon size={13} />
                <span>{source.domaene}</span>
                <ChevronRight size={13} />
              </button>
            ))}
          </div>
        </section>
      )}
    </div>
  )
}
