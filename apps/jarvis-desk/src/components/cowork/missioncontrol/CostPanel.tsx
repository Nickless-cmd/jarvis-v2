import { useEffect, useState } from 'react'
import type { ApiConfig } from '../../../lib/api'
import { getMcCostsDaily, type McDailyCost } from '../../../lib/missionControlApi'

interface DayAgg { day: string; cost: number; tokens: number; calls: number }

/** Cost-panel: pris/tokens pr. dag (aggregeret på tværs af lanes) som simple søjler.
 *  daily_cost_summary giver én række pr. dag PR. lane → vi summerer pr. dag. */
export function CostPanel({ config }: { config: ApiConfig | undefined }) {
  const [rows, setRows] = useState<McDailyCost[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!config) return
    let alive = true
    setLoading(true)
    getMcCostsDaily(config, 14)
      .then((r) => { if (alive) setRows(r) })
      .catch(() => { if (alive) setRows([]) })
      .finally(() => { if (alive) setLoading(false) })
    return () => { alive = false }
  }, [config])

  if (loading) return <div className="cowork-empty">Henter…</div>
  if (rows.length === 0) return <div className="cowork-empty">Ingen omkostningsdata</div>

  const byDay = new Map<string, DayAgg>()
  for (const r of rows) {
    const day = r.day || '?'
    const agg = byDay.get(day) ?? { day, cost: 0, tokens: 0, calls: 0 }
    agg.cost += r.total_cost ?? 0
    agg.tokens += r.total_tokens ?? 0
    agg.calls += r.calls ?? 0
    byDay.set(day, agg)
  }
  const days = [...byDay.values()].sort((a, b) => (a.day < b.day ? 1 : -1)).slice(0, 14)
  const maxTokens = Math.max(1, ...days.map((d) => d.tokens))
  const totalCost = days.reduce((s, d) => s + d.cost, 0)
  const totalTokens = days.reduce((s, d) => s + d.tokens, 0)

  return (
    <div className="mc-cost">
      <div className="mc-cost-totals">
        <div><span className="mc-cost-num">${totalCost.toFixed(2)}</span><span className="mc-cost-lbl">14 dage</span></div>
        <div><span className="mc-cost-num">{fmtNum(totalTokens)}</span><span className="mc-cost-lbl">tokens</span></div>
      </div>
      <div className="mc-cost-bars">
        {days.map((d) => (
          <div key={d.day} className="mc-cost-row">
            <span className="mc-cost-day mc-mono">{d.day.slice(5)}</span>
            <span className="mc-cost-bar-track">
              <span className="mc-cost-bar" style={{ width: `${Math.round((d.tokens / maxTokens) * 100)}%` }} />
            </span>
            <span className="mc-cost-val mc-mono">{fmtNum(d.tokens)}{d.cost > 0 ? ` · $${d.cost.toFixed(2)}` : ''}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function fmtNum(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}
