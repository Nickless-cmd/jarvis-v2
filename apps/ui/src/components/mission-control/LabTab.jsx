import { useEffect, useState } from 'react'
import { RefreshCcw, FlaskConical } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState, Skeleton } from './shared'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'

const FAMILY_COLORS = {
  tool: T.blue,
  runtime: T.accent,
  heartbeat: T.green,
  memory: T.purple,
  cost: T.amber,
  channel: T.accentText,
  approvals: T.amber,
}

function FamilyChip({ family }) {
  const color = FAMILY_COLORS[family] || T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${color}18`, border: `1px solid ${color}35`, color, flexShrink: 0 })}>
      {family || 'other'}
    </span>
  )
}

export function LabTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlLab()
        if (!cancelled) {
          setData(result)
          setFetchedAt(new Date().toISOString())
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  async function refresh() {
    setLoading(true)
    try {
      const result = await backend.getMissionControlLab()
      setData(result)
      setFetchedAt(new Date().toISOString())
    } finally {
      setLoading(false)
    }
  }

  const costs = data?.costs_today || {}
  const db = data?.db_stats || {}

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <FlaskConical size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Lab</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{fetchedAt ? formatFreshness(fetchedAt) : ''}</span>
        <button
          onClick={refresh}
          disabled={loading}
          style={s({ marginLeft: 'auto', padding: '4px 8px', borderRadius: 7, border: `1px solid ${T.border1}`, background: T.bgOverlay, color: T.text2, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 })}
        >
          <RefreshCcw size={11} />
        </button>
      </div>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Kost i dag (USD)" value={loading ? '…' : `$${(costs.total_usd || 0).toFixed(4)}`} />
        <MetricCard label="Input tokens" value={loading ? '…' : (costs.input_tokens || 0).toLocaleString()} />
        <MetricCard label="Output tokens" value={loading ? '…' : (costs.output_tokens || 0).toLocaleString()} />
        <MetricCard label="Kald i dag" value={loading ? '…' : costs.calls ?? 0} />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
        <Card>
          <SectionTitle>Providers — i dag</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={28} />)}
            </div>
          ) : (data?.providers_today || []).length === 0 ? (
            <EmptyState title="Ingen kald endnu">Provider-statistik vises her.</EmptyState>
          ) : (
            <table style={s({ width: '100%', borderCollapse: 'collapse' })}>
              <thead>
                <tr>
                  {['Provider', 'Kost USD', 'Tokens', 'Kald'].map((h) => (
                    <th key={h} style={s({ ...mono, fontSize: 9, color: T.text3, textAlign: 'left', padding: '3px 6px' })}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(data.providers_today || []).map((p) => (
                  <tr key={p.provider}
                    onMouseEnter={(e) => (e.currentTarget.style.background = T.bgHover)}
                    onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                  >
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.accentText })}>{p.provider}</td>
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.text1 })}>{p.cost_usd.toFixed(4)}</td>
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.text1 })}>{(p.input_tokens + p.output_tokens).toLocaleString()}</td>
                    <td style={s({ padding: '5px 6px', ...mono, fontSize: 10, color: T.text1 })}>{p.calls}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card>
          <SectionTitle>DB-statistik</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={24} />)}
            </div>
          ) : (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 0 })}>
              {[
                ['Events i alt', db.events],
                ['Visible runs', db.runs],
                ['Chat sessioner', db.sessions],
                ['Tool-intent godkendelser', db.approvals],
              ].map(([label, val]) => (
                <div key={label} style={s({ display: 'flex', justifyContent: 'space-between', padding: '6px 0', borderBottom: `1px solid ${T.border0}` })}>
                  <span style={s({ fontSize: 11, color: T.text3 })}>{label}</span>
                  <span style={s({ ...mono, fontSize: 11, color: T.text1 })}>{(val ?? 0).toLocaleString()}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>

      <Card>
        <SectionTitle>Seneste events</SectionTitle>
        {loading ? (
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 5 })}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={26} />)}
          </div>
        ) : (data?.recent_events || []).length === 0 ? (
          <EmptyState title="Ingen events endnu">Events vises her efterhånden som de sker.</EmptyState>
        ) : (
          <ScrollPanel maxHeight={240}>
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
              {(data.recent_events || []).map((ev) => (
                <div key={ev.id} style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay })}>
                  <FamilyChip family={ev.family} />
                  <span style={s({ fontSize: 10, color: T.text2, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{ev.kind}</span>
                  <span style={s({ ...mono, fontSize: 9, color: T.text3, flexShrink: 0 })}>{formatFreshness(ev.created_at)}</span>
                </div>
              ))}
            </div>
          </ScrollPanel>
        )}
      </Card>
    </div>
  )
}
