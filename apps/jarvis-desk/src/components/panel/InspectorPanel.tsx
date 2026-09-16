import { ArrowLeft, Bot, File, FileText, Globe, Wrench, X } from 'lucide-react'
import type { ApiConfig } from '../../lib/api'
import type { InspectorTarget } from '../../lib/inspectorTargets'
import { lookupTool } from '../../lib/toolRegistry'
import { ArtifactInspectorBody } from './ArtifactPanel'
import { AgentInspector } from './AgentInspector'
import { SourceInspector } from './SourceInspector'
import { ToolInspector } from './ToolInspector'

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
  return { title: lookupTool(target.tool.name).label, Icon: Wrench }
}

export function InspectorPanel({
  target, config, canGoBack, onBack, onClose, onOpenTarget,
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
      {target?.type === 'artifact' && <ArtifactInspectorBody artifact={target.artifact} config={config} />}
      {target?.type === 'source' && (
        <SourceInspector
          source={target.source}
          tool={target.tool}
          onOpenTool={target.tool ? (tool) => onOpenTarget({ type: 'tool', tool }, true) : undefined}
        />
      )}
      {target?.type === 'tool' && (
        <ToolInspector
          tool={target.tool}
          onOpenSource={(source) => onOpenTarget({ type: 'source', source, tool: target.tool }, true)}
        />
      )}
      {target?.type === 'agent' && (config
        ? <AgentInspector config={config} agent={target.agent} canMessage={target.canMessage} />
        : <div className="artifact-body artifact-empty">Agentdetaljen kræver forbindelse til serveren.</div>)}
      {!target && <div className="artifact-body artifact-empty">Intet at vise endnu.</div>}
    </div>
  )
}
