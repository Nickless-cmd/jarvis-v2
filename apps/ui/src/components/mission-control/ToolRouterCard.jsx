import { useState, useEffect, useCallback } from 'react'
import { Zap, AlertCircle, CheckCircle2, Layers } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel } from './shared'


export function ToolRouterCard() {
  const [state, setState] = useState(null)
  const [error, setError] = useState(null)

  const fetchState = useCallback(async () => {
    try {
      const r = await fetch('/mc/tool-router-state')
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
    const id = setInterval(fetchState, 8000)
    return () => clearInterval(id)
  }, [fetchState])

  if (error) {
    return (
      <Card>
        <div style={s({ ...mono, fontSize: 11, color: T.red, padding: 8 })}>
          tool-router-state error: {error}
        </div>
      </Card>
    )
  }

  if (!state) {
    return <Card><div style={s({ padding: 8, color: T.text3, fontSize: 11 })}>Loading…</div></Card>
  }

  const t = state.totals || {}
  const recent = state.recent_decisions || []
  const missed = state.top_missed_tools_7d || []
  const hist = state.confidence_histogram || []
  const maxBucket = Math.max(1, ...hist)

  return (
    <div>
      <SectionTitle>
        Tool Router{' '}
        <span style={s({ ...mono, fontSize: 11, color: state.enabled ? T.green : T.text3, marginLeft: 8 })}>
          [{state.enabled ? 'enabled ✓' : 'disabled'}]
        </span>
      </SectionTitle>

      <div style={s({ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginTop: 8 })}>
        <MetricCard
          label="Tokens saved (avg/turn)"
          value={(t.avg_tokens_saved_7d || 0).toLocaleString()}
          sub="last 7d"
          icon={Zap}
          color={T.accent}
        />
        <MetricCard
          label="Selection rate"
          value={`${Math.round((1 - (t.fallback_rate_7d || 0)) * 100)}%`}
          sub={`${t.decisions_7d || 0} decisions`}
          icon={CheckCircle2}
          color={T.green}
        />
        <MetricCard
          label="Fallback rate"
          value={`${Math.round((t.fallback_rate_7d || 0) * 100)}%`}
          sub="confidence too low"
          icon={AlertCircle}
          color={(t.fallback_rate_7d || 0) > 0.30 ? T.amber : T.text3}
        />
        <MetricCard
          label="load_more rate"
          value={`${Math.round((t.load_more_rate_7d || 0) * 100)}%`}
          sub="Jarvis fetched extras"
          icon={Layers}
          color={(t.load_more_rate_7d || 0) > 0.15 ? T.amber : T.text3}
        />
      </div>

      <div style={s({ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 12 })}>
        <Card>
          <div style={s({ ...mono, fontSize: 11, color: T.text2, marginBottom: 6 })}>Confidence histogram</div>
          <div style={s({ display: 'flex', gap: 2, alignItems: 'flex-end', height: 56 })}>
            {hist.map((n, i) => (
              <div key={i} style={s({
                flex: 1,
                height: `${(n / maxBucket) * 100}%`,
                background: i < 5 ? T.amber : T.green,
                opacity: 0.7,
                minHeight: n > 0 ? 2 : 0,
              })} title={`${(i * 0.1).toFixed(1)}-${((i + 1) * 0.1).toFixed(1)}: ${n}`} />
            ))}
          </div>
          <div style={s({ ...mono, fontSize: 9, color: T.text3, marginTop: 4 })}>
            0 ─────── 1.0 (threshold = {state.config?.threshold?.toFixed(2)})
          </div>
        </Card>
        <Card>
          <div style={s({ ...mono, fontSize: 11, color: T.text2, marginBottom: 6 })}>Top missed tools (7d)</div>
          <ScrollPanel maxHeight={84}>
            {missed.length > 0 ? (
              missed.map((m, i) => (
                <div key={i} style={s({ display: 'flex', justifyContent: 'space-between', fontSize: 10, ...mono, padding: '2px 4px' })}>
                  <span style={s({ color: T.accent })}>{m.name}</span>
                  <span style={s({ color: T.text3 })}>{m.count}</span>
                </div>
              ))
            ) : (
              <div style={s({ ...mono, fontSize: 10, color: T.text3 })}>(none)</div>
            )}
          </ScrollPanel>
        </Card>
      </div>

      <Card style={{ marginTop: 12 }}>
        <div style={s({ ...mono, fontSize: 11, color: T.text2, marginBottom: 6 })}>Recent decisions</div>
        <ScrollPanel maxHeight={180}>
          {recent.length > 0 ? recent.map((r, i) => (
            <div key={i} style={s({ display: 'flex', gap: 8, alignItems: 'center', padding: '3px 6px', fontSize: 10, ...mono })}>
              <span style={s({ color: T.text3, width: 64 })}>
                {r.at ? new Date(r.at).toLocaleTimeString() : '—'}
              </span>
              <span style={s({ color: r.fallback_used ? T.amber : T.green, width: 32 })}>
                {r.fallback_used ? 'FB' : 'OK'}
              </span>
              <span style={s({ color: T.text2, width: 50 })}>{r.confidence?.toFixed(2)}</span>
              <span style={s({ color: T.accent, width: 36 })}>{r.selected_count}t</span>
              <span style={s({ color: T.text2, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
                {r.preview}
              </span>
              <span style={s({ color: T.text3, width: 50, textAlign: 'right' })}>{r.elapsed_ms}ms</span>
            </div>
          )) : (
            <div style={s({ padding: 8, color: T.text3, fontSize: 11, ...mono })}>
              Ingen decisions endnu — selectoren har ikke kørt en tur. Bootstrap embeddings og prøv igen.
            </div>
          )}
        </ScrollPanel>
      </Card>
    </div>
  )
}
