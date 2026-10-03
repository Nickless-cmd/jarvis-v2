import { X, FileCode2 } from 'lucide-react'
import { ArtifactsView } from '../../views/ArtifactsView'

/**
 * Artefakter ved samtalen — Jarvis' `desk_show_pane('artifact')`.
 *
 * 3/10-2026: desk afviste `artifact` med «Artefakter er ikke et panel ved
 * samtalen — de ligger under «Artefakter» i sidebaren». Det var sandt om
 * SIDEBAREN, men ikke om komponenten: `ArtifactsView` kan vises hvor som
 * helst. Vi genbruger den, så listen og fil-visningen er den samme som i
 * sidebaren — ingen anden sandhed om hvilke filer Jarvis har rørt.
 */
export function ArtifactsPanel({ onOpenCode, onClose }: { onOpenCode: () => void; onClose: () => void }) {
  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <FileCode2 size={14} /> <span className="artifact-title">Artefakter</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      <div className="artifact-body artefakter-body">
        <ArtifactsView onOpenCode={onOpenCode} />
      </div>
    </div>
  )
}
