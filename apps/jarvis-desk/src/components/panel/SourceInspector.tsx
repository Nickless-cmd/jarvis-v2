import { ExternalLink, Wrench } from 'lucide-react'
import type { SourceEvidence, ToolEvidence } from '../../lib/environmentEvidence'
import { lookupTool } from '../../lib/toolRegistry'

function queryFrom(source: SourceEvidence): string {
  const input = source.input ?? {}
  for (const key of ['query', 'url', 'prompt', 'task', 'command']) {
    const value = input[key]
    if (typeof value === 'string' && value.trim()) return value.trim()
  }
  return ''
}

function originLabel(source: SourceEvidence): string {
  if (source.origin === 'assistant_text') return 'Fra svartekst'
  if (source.origin === 'tool_input') return 'Fra tool-input'
  return 'Fra tool-resultat'
}

export function SourceInspector({
  source,
  tool,
  onOpenTool,
}: {
  source: SourceEvidence
  tool?: ToolEvidence
  onOpenTool?: (tool: ToolEvidence) => void
}) {
  const query = queryFrom(source)
  const toolLabel = source.toolName ? lookupTool(source.toolName).label : ''
  return (
    <div className="inspector-body source-inspector">
      <section className="inspector-section">
        <div className="inspector-kicker">Kilde</div>
        <div className="source-domain">{source.domaene}</div>
        <div className="source-url" title={source.url}>{source.url}</div>
        <button
          type="button"
          className="inspector-primary"
          onClick={() => window.open(source.url, '_blank', 'noopener,noreferrer')}
        >
          <ExternalLink size={14} /> Åbn kilde
        </button>
      </section>

      <section className="inspector-section">
        <div className="inspector-kicker">Proveniens</div>
        <dl className="inspector-facts">
          <div><dt>Oprindelse</dt><dd>{originLabel(source)}</dd></div>
          {toolLabel && <div><dt>Tool</dt><dd>{toolLabel}</dd></div>}
          {source.toolUseId && <div><dt>Tool-ID</dt><dd className="inspector-mono">{source.toolUseId}</dd></div>}
        </dl>
        {query && (
          <div className="inspector-block">
            <div className="inspector-label">Søgning eller hentning</div>
            <div>{query}</div>
          </div>
        )}
        {tool && onOpenTool && (
          <button type="button" className="inspector-secondary" onClick={() => onOpenTool(tool)}>
            <Wrench size={14} /> Vis tool-resultat
          </button>
        )}
      </section>

      {source.resultExcerpt && (
        <section className="inspector-section">
          <div className="inspector-kicker">Relevant resultat</div>
          <pre className="inspector-pre">{source.resultExcerpt}</pre>
        </section>
      )}
    </div>
  )
}
