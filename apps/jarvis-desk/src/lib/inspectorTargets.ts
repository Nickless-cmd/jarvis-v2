import type { Artifact } from './artifacts'
import type { AgentReference, SourceEvidence, ToolEvidence } from './environmentEvidence'

export type InspectorTarget =
  | { type: 'artifact'; artifact: Artifact }
  | { type: 'agent'; agent: AgentReference; canMessage: boolean }
  | { type: 'source'; source: SourceEvidence; tool?: ToolEvidence }
  | { type: 'tool'; tool: ToolEvidence }
