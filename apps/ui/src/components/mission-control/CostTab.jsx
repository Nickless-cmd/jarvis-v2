import { DollarSign, Hash, AlertCircle } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard } from './shared'

export function CostTab({ data }) {
  const cost = data || {}
  const providers = cost.providers || []

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="24h Cost (USD)" value={`$${Number(cost.cost_24h_usd || 0).toFixed(4)}`} icon={DollarSign} />
        <MetricCard label="24h Tokens" value={(cost.tokens_24h || 0).toLocaleString()} icon={Hash} />
        <MetricCard label="Unknown Pricing (24h)" value={cost.unknown_pricing_24h || 0} icon={AlertCircle} />
      </div>

      <Card>
        <SectionTitle>Top Providers (24h)</SectionTitle>
        <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
          <thead>
            <tr>
              {['Provider', 'Cost USD', 'Tokens', 'Calls'].map((h) => (
                <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '4px 8px' })}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {providers.map((p) => (
              <tr
                key={p.provider}
                onMouseEnter={(e) => (e.currentTarget.style.background = T.bgHover)}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
              >
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.accentText })}>{p.provider}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{Number(p.cost_usd || 0).toFixed(4)}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.tokens}</td>
                <td style={s({ padding: '7px 8px', ...mono, fontSize: 11, color: T.text1 })}>{p.calls}</td>
              </tr>
            ))}
            {providers.length === 0 && (
              <tr>
                <td colSpan={4} style={s({ padding: '8px', ...mono, fontSize: 10, color: T.text3 })}>No cost data yet</td>
              </tr>
            )}
          </tbody>
        </table>
      </Card>
    </div>
  )
}
