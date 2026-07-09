import { useState } from 'react'
import { FileText, Loader2 } from 'lucide-react'
import { getPaste } from '../../lib/pasteStore'
import type { ApiConfig } from '../../lib/api'

/** Reference-chip for en eksternaliseret paste i en besked. Klik → lazy GET /paste/{id}
 *  → udfold fuld tekst. Uden config (eller ved fejl) forbliver chippen kompakt. */
export function PasteReferenceChip({
  pasteId,
  lineCount,
  config,
}: {
  pasteId: string
  lineCount: number
  config?: ApiConfig
}) {
  const [expanded, setExpanded] = useState(false)
  const [text, setText] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(false)

  const toggle = () => {
    if (expanded) {
      setExpanded(false)
      return
    }
    if (text !== null) {
      setExpanded(true)
      return
    }
    if (!config) {
      setError(true)
      return
    }
    setLoading(true)
    setError(false)
    getPaste(config, pasteId)
      .then((r) => {
        setText(r.text)
        setExpanded(true)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }

  return (
    <span className="paste-ref">
      <button type="button" className="paste-ref-chip" onClick={toggle} title="Indsat tekst">
        {loading ? <Loader2 size={13} className="spin" /> : <FileText size={13} />}
        <span className="paste-ref-label">
          Indsat tekst +{lineCount} linjer{error ? ' (kunne ikke hentes)' : ''}
        </span>
      </button>
      {expanded && text !== null && (
        <pre className="paste-ref-body">{text}</pre>
      )}
    </span>
  )
}
