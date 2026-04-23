import { useEffect, useState } from 'react'
import { RefreshCcw, ShieldCheck } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState, Skeleton } from './shared'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'

function IntegrationRow({ label, ok }) {
  const color = ok ? T.green : T.text3
  return (
    <div style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 0' })}>
      <div style={s({ width: 7, height: 7, borderRadius: '50%', background: color, boxShadow: ok ? `0 0 6px ${color}` : 'none', flexShrink: 0 })} />
      <span style={s({ fontSize: 11, color: ok ? T.text2 : T.text3 })}>{label}</span>
      <span style={s({ ...mono, fontSize: 9, color: T.text3, marginLeft: 'auto' })}>{ok ? 'konfigureret' : 'ikke sat op'}</span>
    </div>
  )
}

function StateChip({ state }) {
  const colorMap = {
    pending: T.amber,
    approved: T.green,
    denied: T.red,
    expired: T.text3,
  }
  const color = colorMap[state] || T.text3
  return (
    <span style={s({ ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10, background: `${color}18`, border: `1px solid ${color}35`, color })}>
      {state}
    </span>
  )
}

export function HardeningTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [fetchedAt, setFetchedAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlHardening()
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
      const result = await backend.getMissionControlHardening()
      setData(result)
      setFetchedAt(new Date().toISOString())
    } finally {
      setLoading(false)
    }
  }

  const pending = data?.pending ?? 0
  const integrations = data?.integrations || {}

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <ShieldCheck size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Hardening</span>
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
        <MetricCard
          label="Afventer"
          value={loading ? '…' : pending}
          color={pending > 0 ? T.amber : undefined}
          alert={pending > 0}
        />
        <MetricCard label="Godkendt i dag" value={loading ? '…' : data?.approved_today ?? 0} color={T.green} />
        <MetricCard label="Afvist i dag" value={loading ? '…' : data?.denied_today ?? 0} color={data?.denied_today > 0 ? T.red : undefined} />
        <MetricCard label="Autonomi-niveau" value={loading ? '…' : (data?.autonomy_level || 'ukendt')} />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: 12 })}>
        <Card>
          <SectionTitle>Integrationer</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={24} />)}
            </div>
          ) : (
            <>
              <IntegrationRow label="Telegram" ok={integrations.telegram} />
              <IntegrationRow label="Discord" ok={integrations.discord} />
              <IntegrationRow label="Home Assistant" ok={integrations.home_assistant} />
              <IntegrationRow label="Anthropic API" ok={integrations.anthropic} />
            </>
          )}
        </Card>

        <Card>
          <SectionTitle>Seneste tool-intent anmodninger</SectionTitle>
          {loading ? (
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} height={28} />)}
            </div>
          ) : (data?.recent_approvals || []).length === 0 ? (
            <EmptyState title="Ingen anmodninger endnu">Tool-intent godkendelser vises her.</EmptyState>
          ) : (
            <ScrollPanel maxHeight={200}>
              <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
                {(data.recent_approvals || []).map((row, i) => (
                  <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay })}>
                    <span style={s({ ...mono, fontSize: 10, color: T.accentText, minWidth: 120, flexShrink: 0 })}>{row.intent_type}</span>
                    <span style={s({ fontSize: 10, color: T.text3, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>{row.intent_target}</span>
                    <StateChip state={row.approval_state} />
                  </div>
                ))}
              </div>
            </ScrollPanel>
          )}
        </Card>
      </div>
    </div>
  )
}
