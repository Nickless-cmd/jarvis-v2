import { useEffect, useMemo, useState } from 'react'
import { X, Search } from 'lucide-react'
import type { ToolEvidence } from '../lib/environmentEvidence'
import { erUsagesTool, parseUsages } from '../lib/usagesKontrakt'
import '../styles/kode-flader.css'

/** Usages-panel: viser resultatet af Jarvis' `find_usages`/`find_symbol` (Serena LSP / ripgrep).
 *  Læser de tool-kald der allerede ligger i samtalens evidens — panelet kalder intet selv.
 *  Klik på en hit åbner filen i fil-panelet. */
export function UsagesPanel({
  tools, onOpenFile, onClose,
}: {
  tools: ToolEvidence[]
  onOpenFile: (path: string, line: number) => void
  onClose: () => void
}) {
  const opslag = useMemo(() => tools.filter(erUsagesTool), [tools])
  const [valgtId, setValgtId] = useState('')
  // Nyeste opslag er standard; valgt id der er forsvundet falder tilbage til det nyeste.
  const valgt = opslag.find((t) => t.id === valgtId) ?? opslag[opslag.length - 1]
  useEffect(() => { if (valgtId && !opslag.some((t) => t.id === valgtId)) setValgtId('') }, [opslag, valgtId])
  const parsed = valgt ? parseUsages(valgt) : null

  return (
    <div className="artifact-panel">
      <div className="artifact-head">
        <Search size={14} /> <span className="artifact-title">Usages</span>
        <button type="button" className="artifact-close" aria-label="Luk panel" onClick={onClose}>
          <X size={15} />
        </button>
      </div>
      {opslag.length > 1 && (
        <div className="usages-kilde">
          {opslag.map((t) => (
            <button key={t.id} type="button" className={t === valgt ? 'active' : ''}
              onClick={() => setValgtId(t.id)}>
              {t.name === 'find_usages' ? 'Brug' : 'Symbol'}: {String(t.input.name ?? t.input.symbol ?? '?')}
            </button>
          ))}
        </div>
      )}
      <div className="artifact-body">
        {!valgt && (
          <div className="artifact-empty">
            Ingen opslag endnu. Bed Jarvis om at finde brugen af et symbol (find_usages / find_symbol).
          </div>
        )}
        {parsed && !parsed.ok && <div className="artifact-error">{parsed.fejl}</div>}
        {parsed?.ok && (
          <>
            <div className="usages-meta">
              {parsed.svar.hits.length} {parsed.svar.tool === 'find_usages' ? 'brug af' : 'definitioner af'}{' '}
              <b>{parsed.svar.navn}</b>
              {parsed.svar.backend && <> · via {parsed.svar.backend === 'lsp' ? 'LSP (Serena)' : parsed.svar.backend}</>}
              {parsed.svar.truncated && ' · afkortet'}
            </div>
            {parsed.svar.hits.length === 0 && <div className="artifact-empty">Ingen fund.</div>}
            <ul className="usages-liste">
              {parsed.svar.hits.map((h, i) => (
                <li key={`${h.file}:${h.line}:${i}`}>
                  <button type="button" className="usages-hit" title={`Åbn ${h.file}`}
                    onClick={() => onOpenFile(h.file, h.line)}>
                    <span className="usages-sti">{h.file}:{h.line}</span>
                    {h.enclosing && <span className="usages-meta"> i {h.enclosing}</span>}
                    {h.kind && <span className="usages-meta"> · {h.kind}</span>}
                    {h.snippet && <span className="usages-snippet">{h.snippet.trim()}</span>}
                  </button>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  )
}
