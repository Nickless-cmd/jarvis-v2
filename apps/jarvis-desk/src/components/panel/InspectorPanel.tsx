import { ArrowLeft, Bot, File, FileText, Globe, Wrench, X } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import type { InspectorTarget } from '../../lib/inspectorTargets'
import { ArtifactInspectorBody } from './ArtifactPanel'

export interface InspectorPanelProps {
  target: InspectorTarget | null
  config?: ApiConfig
  canGoBack: boolean
  onBack: () => void
  onClose: () => void
  onOpenTarget: (target: InspectorTarget, rememberCurrent?: boolean) => void
}

function meta(target: InspectorTarget | null) {
  if (!target) return { title: 'Panel', Icon: File }
  if (target.type === 'artifact') return { title: target.artifact.title, Icon: target.artifact.kind === 'markdown' ? FileText : File }
  if (target.type === 'agent') return { title: target.agent.role || target.agent.goal || target.agent.agentId, Icon: Bot }
  if (target.type === 'source') return { title: target.source.domaene, Icon: Globe }
  return { title: target.tool.name, Icon: Wrench }
}

export function InspectorPanel({
  target, config, canGoBack, onBack, onClose,
}: InspectorPanelProps) {
  const { title, Icon } = meta(target)
  const showBack = canGoBack || (!!target && target.type !== 'artifact')
  return (
    <div className="artifact-panel inspector-panel">
      <div className="artifact-head inspector-head">
        {showBack && (
          <button type="button" className="artifact-close inspector-back" aria-label="Tilbage til Miljø" onClick={onBack}>
            <ArrowLeft size={15} />
          </button>
        )}
        <Icon size={14} />
        <span className="artifact-title">{title}</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      {target?.type === 'artifact'
        ? <ArtifactInspectorBody artifact={target.artifact} config={config} />
        : (
          <div className="artifact-body artifact-empty">
            {target ? 'Detaljer indlæses i næste trin.' : 'Intet at vise endnu.'}
          </div>
        )}
    </div>
  )
}
