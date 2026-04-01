import { DollarSign, Hash, AlertCircle } from 'lucide-react'
import { MetricCard } from '../shared/MetricCard'
import { SectionTitle } from '../shared/SectionTitle'

export function CostTab({ data }) {
  const cost = data || {}
  const providers = cost.providers || []

  return (
    <div className="mc-tab-page">
      <div className="mc-cost-cards">
        <MetricCard label="24h Cost (USD)" value={`$${Number(cost.cost_24h_usd || 0).toFixed(4)}`} icon={DollarSign} />
        <MetricCard label="24h Tokens" value={(cost.tokens_24h || 0).toLocaleString()} icon={Hash} />
        <MetricCard label="Unknown Pricing (24h)" value={cost.unknown_pricing_24h || 0} icon={AlertCircle} />
      </div>

      <div className="support-card">
        <SectionTitle>Top Providers (24h)</SectionTitle>
        <table className="mc-table">
          <thead>
            <tr>
              {['Provider', 'Cost USD', 'Tokens', 'Calls'].map(h => (
                <th key={h} className="mono">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {providers.map(p => (
              <tr key={p.provider}>
                <td className="mono" style={{ color: '#5ab8a0' }}>{p.provider}</td>
                <td className="mono">{Number(p.cost_usd || 0).toFixed(4)}</td>
                <td className="mono">{p.tokens}</td>
                <td className="mono">{p.calls}</td>
              </tr>
            ))}
            {providers.length === 0 && (
              <tr><td colSpan={4} className="mc-table-empty mono">No cost data yet</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
