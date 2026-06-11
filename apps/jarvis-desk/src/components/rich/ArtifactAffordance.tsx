import { ArrowUpRight } from 'lucide-react'
import type { Artifact } from '../../lib/artifacts'
import { usePanel } from '../../hooks/usePanel'

export function ArtifactAffordance({ artifact }: { artifact: Artifact }) {
  const panel = usePanel()
  return (
    <button type="button" className="artifact-affordance" onClick={() => panel.open_(artifact)}>
      <ArrowUpRight size={13} /> Åbn {artifact.title}
    </button>
  )
}
