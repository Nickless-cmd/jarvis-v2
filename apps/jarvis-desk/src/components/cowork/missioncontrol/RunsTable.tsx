import { useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import type { McRun } from '../../../lib/missionControlApi'
import { StatusChip } from './StatusChip'
import { RunDetail } from './RunDetail'

type Filter = 'alle' | 'kører' | 'fejlet'

/** Runs-tabel: filtrerbar liste over kørsler; klik en række → drill-down (RunDetail).
 *  Landingsfladen for "hvad sker der". */
export function RunsTable({ config, runs }: { config: ApiConfig | undefined; runs: McRun[] }) {
  const [filter, setFilter] = useState<Filter>('alle')
  const [selected, setSelected] = useState<string | null>(null)

  const shown = runs.filter((r) => {
    const s = String(r.status || '').toLowerCase()
    if (filter === 'kører') return s === 'running' || s === 'active' || s === 'working'
    if (filter === 'fejlet') return s === 'failed' || s === 'cancelled' || s === 'error'
    return true
  })

  return (
    <div className="mc-runs">
      <div className="mc-filters">
        {(['alle', 'kører', 'fejlet'] as Filter[]).map((f) => (
          <button
            key={f}
            type="button"
            className={`mc-filter ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f}
          </button>
        ))}
      </div>

      {shown.length === 0 ? (
        <div className="cowork-empty">Ingen kørsler</div>
      ) : (
        <div className="mc-table">
          {shown.map((r) => (
            <button
              key={r.run_id}
              type="button"
              className={`mc-row ${selected === r.run_id ? 'active' : ''}`}
              onClick={() => setSelected((cur) => (cur === r.run_id ? null : r.run_id))}
            >
              <StatusChip status={r.status} />
              <span className="mc-row-main">
                <span className="mc-row-title">{r.text_preview?.slice(0, 80) || r.capability_id || 'kørsel'}</span>
                <span className="mc-row-sub mc-mono">{r.provider || r.lane || ''} {r.model || ''}</span>
              </span>
              <span className="mc-row-at">{r.started_at ? fmtDay(r.started_at) : ''}</span>
            </button>
          ))}
        </div>
      )}

      {selected && (
        <RunDetail config={config} runId={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

function fmtDay(iso: string): string {
  try {
    return new Date(iso).toLocaleString('da-DK', {
      day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit',
    })
  } catch {
    return iso
  }
}
