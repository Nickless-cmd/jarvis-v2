import { useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import type { McRun } from '../../../lib/missionControlApi'
import { StatusChip } from './StatusChip'
import { RunDetail } from './RunDetail'
import { spandForRun, type KoeSpand } from '../../../lib/coworkApi'

// «Til gennemsyn» = afbrudte koersler. Bjoern 15/9-2026: «afventer dig mangler
// til gemmensyn som arbejde havde». Han havde ret — den spand fandtes i den
// slettede WorkQueue og havde intet modstykke i MC. «fejlet» daekker
// failed/cancelled/error, saa `interrupted` faldt kun i «alle».
//
// Maalt paa 30 dage: 2.861 completed, 78 INTERRUPTED, 13 failed, 13 cancelled.
// Afbrudte er den stoerste ikke-faerdige kategori — og hver af dem er
// potentielt halvt arbejde der venter paa et blik.
//
// Kortlaegningen status→spand genbruges fra coworkApi i stedet for en ny
// liste her. Den stod uden kaldere efter WorkQueue blev slettet, og to
// lister ville vaere dobbelt sandhed om det samme.
// Alle fire spande fra den gamle «Arbejde» staar nu som selvstaendige filtre
// (Bjoern 15/9-2026: «ja behold kører nu og færdig som selvstændige»), med hans
// egne etiketter. Femte spand — «Venter paa dig» — er godkendelser og bor i
// «Afventer dig»/Godkendelser, ikke i runs-tabellen.
//
// Kortlaegningen daekker praecis spandene, saa hver koersel falder i ét og kun
// ét filter. Det er testet: summen af de fire er lig antallet i «alle».
type Filter = 'alle' | 'kører nu' | 'til gennemsyn' | 'fejlet' | 'færdig'

const SPAND_FOR_FILTER: Record<Exclude<Filter, 'alle'>, KoeSpand> = {
  'kører nu': 'aktiv',
  'til gennemsyn': 'til_gennemsyn',
  'fejlet': 'fejlet',
  'færdig': 'faerdig',
}

/** Runs-tabel: filtrerbar liste over kørsler; klik en række → drill-down (RunDetail).
 *  Landingsfladen for "hvad sker der". */
export function RunsTable({ config, runs }: { config: ApiConfig | undefined; runs: McRun[] }) {
  const [filter, setFilter] = useState<Filter>('alle')
  const [selected, setSelected] = useState<string | null>(null)

  const spandFor = (r: McRun) => spandForRun(String(r.status || ''))
  const shown = filter === 'alle'
    ? runs
    : runs.filter((r) => spandFor(r) === SPAND_FOR_FILTER[filter])
  const antal = (f: Filter) =>
    f === 'alle' ? runs.length : runs.filter((r) => spandFor(r) === SPAND_FOR_FILTER[f]).length

  return (
    <div className="mc-runs">
      <div className="mc-filters">
        {(['alle', 'kører nu', 'til gennemsyn', 'fejlet', 'færdig'] as Filter[]).map((f) => {
          const n = antal(f)
          return (
            <button
              key={f}
              type="button"
              className={`mc-filter ${filter === f ? 'active' : ''}`}
              onClick={() => setFilter(f)}
            >
              {/* Tallet staar paa knappen, saa man kan SE at der ligger noget
                  til gennemsyn uden foerst at klikke sig ind. */}
              {f}{n > 0 && <span className="mc-filter-antal">{n}</span>}
            </button>
          )
        })}
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
