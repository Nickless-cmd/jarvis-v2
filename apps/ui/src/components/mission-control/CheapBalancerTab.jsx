import { useState, useEffect, useCallback } from 'react'
import { RefreshCcw, Zap, ShieldCheck, ShieldOff, AlertCircle, CheckCircle2 } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState } from './shared'

function statusEmoji(slot) {
  if (slot.manually_disabled) return '⚫'
  if (slot.current_weight > 0.3) return '🟢'
  if (slot.current_weight > 0.05) return '🟡'
  return '🔴'
}

function HeadroomBar({ pct }) {
  const w = Math.max(0, Math.min(100, pct ?? 0))
  const color = w > 60 ? T.green : w > 20 ? T.amber : T.red
  return (
    <div style={s({ width: '100%', height: 4, background: T.border0, borderRadius: 2, overflow: 'hidden', marginTop: 4 })}>
      <div style={s({ width: `${w}%`, height: '100%', background: color, transition: 'width 0.3s' })} />
    </div>
  )
}

function SlotCard({ slot, onAction }) {
  const emoji = statusEmoji(slot)
  const limits = []
  if (slot.rpm_limit) limits.push(`${slot.rpm_used_now}/${slot.rpm_limit} RPM`)
  if (slot.daily_limit) limits.push(`${slot.daily_used_today}/${slot.daily_limit}/day`)
  if (!slot.rpm_limit && !slot.daily_limit) limits.push('unlimited')

  const successRate = slot.success_rate != null ? `${(slot.success_rate * 100).toFixed(1)}% ok` : null

  return (
    <Card>
      <div style={s({ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 })}>
        <div style={s({ ...mono, fontSize: 12, color: T.text1, fontWeight: 600 })}>
          {emoji} {slot.slot_id}
        </div>
        <div style={s({ ...mono, fontSize: 11, color: T.text3 })}>weight {slot.current_weight.toFixed(2)}</div>
      </div>
      <div style={s({ ...mono, fontSize: 10, color: T.text3, marginBottom: 4 })}>
        {slot.is_public_proxy ? 'public-proxy' : 'paid'} · {limits.join(' · ')}
        {slot.total_calls > 0 && successRate ? ` · ${slot.total_calls} calls · ${successRate}` : ''}
      </div>
      <HeadroomBar pct={slot.headroom_pct} />
      {slot.cooldown_until ? (
        <div style={s({ ...mono, fontSize: 10, color: T.red, marginTop: 6 })}>
          Cooldown til {new Date(slot.cooldown_until).toLocaleTimeString()} · {slot.cooldown_reason || '(no reason)'}
        </div>
      ) : null}
      <div style={s({ display: 'flex', gap: 6, marginTop: 8 })}>
        {slot.breaker_level > 0 ? (
          <button
            onClick={() => onAction(`/mc/cheap-balancer/slot/${encodeURIComponent(slot.slot_id)}/reset`)}
            style={s({
              ...mono, fontSize: 10, padding: '3px 8px', borderRadius: 4,
              background: `${T.amber}25`, border: `1px solid ${T.amber}50`, color: T.amber, cursor: 'pointer',
            })}
          >
            Reset breaker (L{slot.breaker_level})
          </button>
        ) : null}
        {slot.manually_disabled ? (
          <button
            onClick={() => onAction(`/mc/cheap-balancer/slot/${encodeURIComponent(slot.slot_id)}/enable`)}
            style={s({
              ...mono, fontSize: 10, padding: '3px 8px', borderRadius: 4,
              background: `${T.green}25`, border: `1px solid ${T.green}50`, color: T.green, cursor: 'pointer',
            })}
          >
            Enable
          </button>
        ) : (
          <button
            onClick={() => onAction(`/mc/cheap-balancer/slot/${encodeURIComponent(slot.slot_id)}/disable`)}
            style={s({
              ...mono, fontSize: 10, padding: '3px 8px', borderRadius: 4,
              background: `${T.red}18`, border: `1px solid ${T.red}40`, color: T.red, cursor: 'pointer',
            })}
          >
            Disable
          </button>
        )}
      </div>
    </Card>
  )
}

function RecentCallRow({ call }) {
  const ok = call.status === 'ok'
  return (
    <div style={s({ display: 'flex', gap: 8, alignItems: 'center', padding: '3px 6px', fontSize: 10, ...mono })}>
      <span style={s({ color: T.text3, width: 64 })}>{new Date(call.at).toLocaleTimeString()}</span>
      <span style={s({ color: ok ? T.green : T.red, width: 14 })}>{ok ? '✓' : '✗'}</span>
      <span style={s({ color: T.text2, width: 140, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
        {call.daemon || '(unnamed)'}
      </span>
      <span style={s({ color: T.accent, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
        {call.slot_id}
      </span>
      <span style={s({ color: T.text3, width: 60, textAlign: 'right' })}>{call.latency_ms}ms</span>
      {call.error ? (
        <span style={s({ color: T.red, width: 100, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
          {call.error}
        </span>
      ) : null}
    </div>
  )
}

export function CheapBalancerTab() {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)

  const fetchState = useCallback(async () => {
    try {
      const r = await fetch('/mc/cheap-balancer-state')
      if (!r.ok) throw new Error(`HTTP ${r.status}`)
      const data = await r.json()
      setState(data)
      setError(null)
    } catch (e) {
      setError(String(e))
    }
  }, [])

  useEffect(() => {
    fetchState()
    const id = setInterval(fetchState, 4000)
    return () => clearInterval(id)
  }, [fetchState])

  const action = useCallback(
    async (path) => {
      await fetch(path, { method: 'POST' })
      fetchState()
    },
    [fetchState],
  )

  if (error) {
    return (
      <div style={s({ padding: 24 })}>
        <EmptyState title="Balancer state unavailable" description={error} />
      </div>
    )
  }

  if (!state) {
    return <div style={s({ padding: 24, color: T.text3 })}>Loading…</div>
  }

  return (
    <div style={s({ padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'space-between' })}>
        <SectionTitle>
          Cheap Lane Balancer{' '}
          <span style={s({ ...mono, fontSize: 11, color: state.enabled ? T.green : T.text3, marginLeft: 8 })}>
            [{state.enabled ? 'enabled ✓' : 'disabled'}]
          </span>
        </SectionTitle>
        <button
          onClick={() => action('/mc/cheap-balancer/refresh-pool')}
          style={s({
            ...mono, fontSize: 11, padding: '6px 12px', borderRadius: 4,
            background: `${T.accent}18`, border: `1px solid ${T.accent}40`, color: T.accent, cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          })}
        >
          <RefreshCcw size={12} /> Refresh pool
        </button>
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 })}>
        <MetricCard label="Pool size" value={state.pool_size} sub="total slots" icon={Zap} color={T.accent} />
        <MetricCard label="Eligible now" value={state.eligible_now} sub="weight > 0" icon={CheckCircle2} color={T.green} />
        <MetricCard label="Blocked now" value={state.blocked_now} sub="cooldown / disabled" icon={AlertCircle} color={state.blocked_now > 0 ? T.amber : T.text3} />
        <MetricCard label="Recent calls" value={state.recent_calls?.length || 0} sub="last 75" icon={ShieldCheck} color={T.text2} />
      </div>

      <div>
        <SectionTitle>Slots (sorted by weight)</SectionTitle>
        <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(360px, 1fr))', gap: 10, marginTop: 8 })}>
          {state.slots.map((slot) => (
            <SlotCard key={slot.slot_id} slot={slot} onAction={action} />
          ))}
        </div>
      </div>

      <div>
        <SectionTitle>Recent calls (newest first)</SectionTitle>
        <Card style={{ marginTop: 8 }}>
          <ScrollPanel maxHeight={320}>
            {state.recent_calls?.length > 0 ? (
              state.recent_calls.map((c, i) => <RecentCallRow key={i} call={c} />)
            ) : (
              <div style={s({ padding: 12, color: T.text3, fontSize: 11, ...mono })}>No calls yet.</div>
            )}
          </ScrollPanel>
        </Card>
      </div>
    </div>
  )
}
