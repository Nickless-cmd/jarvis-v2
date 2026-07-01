import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import type { ApiConfig } from '../../../lib/api'
import { getMcRunDetail, type McRunDetail } from '../../../lib/missionControlApi'
import { StatusChip } from './StatusChip'

/** Enkelt-run drill-down: run-metadata + trin-tidslinje (dens hændelser). Åbnes fra
 *  RunsTable. Token/pris pr. run findes ikke i skemaet → vises ikke (ærligt). */
export function RunDetail({
  config,
  runId,
  onClose,
}: {
  config: ApiConfig | undefined
  runId: string
  onClose: () => void
}) {
  const [detail, setDetail] = useState<McRunDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!config) return
    let alive = true
    setLoading(true)
    getMcRunDetail(config, runId)
      .then((d) => { if (alive) setDetail(d) })
      .catch(() => { if (alive) setDetail(null) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [config, runId])

  const run = detail?.run
  return (
    <div className="mc-rundetail">
      <div className="mc-rundetail-head">
        <div className="mc-rundetail-title">
          <StatusChip status={run?.status} />
          <span className="mc-mono">{runId.slice(0, 18)}</span>
        </div>
        <button type="button" className="mc-icon-btn" onClick={onClose} aria-label="Luk">
          <X size={15} />
        </button>
      </div>

      {loading ? (
        <div className="cowork-empty">Henter…</div>
      ) : !run && (detail?.steps.length ?? 0) === 0 ? (
        <div className="cowork-empty">Ingen detaljer for dette run</div>
      ) : (
        <>
          {run && (
            <div className="mc-rundetail-meta">
              {run.provider && <span>{run.provider}</span>}
              {run.model && <span className="mc-mono">{run.model}</span>}
              {run.lane && <span>lane: {run.lane}</span>}
              {run.started_at && <span>start: {fmt(run.started_at)}</span>}
              {run.finished_at && <span>slut: {fmt(run.finished_at)}</span>}
            </div>
          )}
          {run?.error && <div className="mc-rundetail-error">{run.error}</div>}
          {run?.text_preview && <div className="mc-rundetail-preview">{run.text_preview}</div>}

          <div className="mc-rundetail-steps-head">Trin ({detail?.steps.length ?? 0})</div>
          <ol className="mc-steps">
            {(detail?.steps ?? []).map((s, i) => (
              <li key={i} className="mc-step">
                <span className="mc-step-dot" />
                <div className="mc-step-body">
                  <div className="mc-step-kind">
                    {s.kind}{s.tool ? <span className="mc-step-tool"> · {s.tool}</span> : null}
                  </div>
                  {s.summary && <div className="mc-step-summary">{s.summary}</div>}
                </div>
                {s.at && <span className="mc-step-at">{fmt(s.at)}</span>}
              </li>
            ))}
            {(detail?.steps.length ?? 0) === 0 && (
              <li className="cowork-empty">Ingen hændelser fanget for dette run</li>
            )}
          </ol>
        </>
      )}
    </div>
  )
}

function fmt(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString('da-DK', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  } catch {
    return iso
  }
}
