import { useCallback, useEffect, useRef, useState } from 'react'
import { Activity, ChevronDown, ChevronRight, ShieldAlert, Zap, Brain, X } from 'lucide-react'
import {
  getCentralRealtime, streamCentral, getCentralNerve, toggleCentralNerve,
  type CentralSnapshot, type CentralFeedItem, type CentralNerveDetail, type ApiConfig,
} from '../../lib/api'

/** Real-time owner-vindue ind i Den Intelligente Central. Sidder under miljø-feltet i
 *  code mode. Snapshot-poll (~2s) for status/clusters/flag/læring + SSE-live-feed for
 *  nerve-fyringer. Klik en nerve → spor + lokation + tænd/sluk. Kun owner (403 ellers). */
export function CentralPanel({ config, isOwner }: { config?: ApiConfig; isOwner?: boolean }) {
  const [snap, setSnap] = useState<CentralSnapshot | null>(null)
  const [liveFeed, setLiveFeed] = useState<CentralFeedItem[]>([])
  const [collapsed, setCollapsed] = useState(false)
  const [showLearning, setShowLearning] = useState(false)
  const [denied, setDenied] = useState(false)
  const [detail, setDetail] = useState<CentralNerveDetail | null>(null)
  const timer = useRef<ReturnType<typeof setInterval> | null>(null)
  const sse = useRef<{ abort: () => void } | null>(null)

  // Snapshot-poll (alt undtagen feed'en).
  useEffect(() => {
    if (!config || !isOwner || collapsed || denied) return
    let cancelled = false
    const tick = () => {
      getCentralRealtime(config)
        .then((s) => { if (!cancelled) setSnap(s) })
        .catch((e) => { if (!cancelled && String(e).includes('403')) setDenied(true) })
    }
    tick()
    timer.current = setInterval(tick, 2000)
    return () => { cancelled = true; if (timer.current) clearInterval(timer.current) }
  }, [config, isOwner, collapsed, denied])

  // SSE-live-feed (ægte realtid). Reconnect ved drop.
  useEffect(() => {
    if (!config || !isOwner || collapsed || denied) return
    let stopped = false
    const connect = () => {
      if (stopped) return
      sse.current = streamCentral(config,
        (item) => setLiveFeed((f) => [item, ...f].slice(0, 26)),
        () => { if (!stopped) setTimeout(connect, 1500) })
    }
    connect()
    return () => { stopped = true; sse.current?.abort() }
  }, [config, isOwner, collapsed, denied])

  const openNerve = useCallback((nerve: string) => {
    if (!config) return
    getCentralNerve(config, nerve).then(setDetail).catch(() => undefined)
  }, [config])

  const doToggle = useCallback((nerve: string, enabled: boolean) => {
    if (!config) return
    toggleCentralNerve(config, nerve, enabled).then(() => openNerve(nerve)).catch(() => undefined)
  }, [config, openNerve])

  if (!isOwner || denied) return null

  const status = snap?.status ?? 'green'
  const cov = snap?.coverage ?? {}
  const diag = snap?.diagnose ?? {}
  const feed = liveFeed.length > 0 ? liveFeed : (snap?.feed ?? [])
  const incidents = snap?.incidents ?? []
  const breakers = snap?.open_breakers ?? []
  const drift = snap?.config_drift
  const learn = snap?.learning ?? {}
  const clusters = snap?.clusters ?? []
  const anomalies = snap?.anomalies ?? {}
  const anomCounts = anomalies.counts ?? {}
  const anomRecent = anomalies.recent ?? []

  return (
    <aside className="central-panel" aria-label="Den Intelligente Central">
      <div className="central-head">
        <span className={`central-dot central-dot-${status}`} title={`Status: ${status}`} />
        <span className="central-title"><Activity size={13} /> Central</span>
        <button type="button" className="central-collapse" onClick={() => setCollapsed((c) => !c)}
          aria-label="Skjul/vis Central" title="Skjul/vis Central">
          {collapsed ? <ChevronRight size={14} /> : <ChevronDown size={14} />}
        </button>
      </div>

      {!collapsed && (
        <>
          {/* Lag 1 — puls */}
          <div className="central-pulse">
            <span className="central-cov">{cov.nerves ?? '—'} nerver · {cov.clusters ?? '—'} clusters</span>
            <span className={`central-diag ${diag.degraded ? 'is-bad' : 'is-ok'}`}>
              {diag.degraded ? 'degraderet' : 'decide+observe ✓'}
            </span>
          </div>

          {/* Cluster-grid — grøn/gul/rød/idle pr. cluster (se ét cluster brække/gå offline) */}
          {clusters.length > 0 && (
            <div className="central-grid" title="Clusters — grøn=fyrer · gul=fejl · rød=brækket · grå=stille">
              {clusters.map((c) => (
                <span key={c.cluster} className={`central-cell central-cell-${c.status}`}
                  title={`${c.cluster}${c.security ? ' 🔒' : ''} — ${c.status}`}>
                  {c.security && <i className="central-cell-lock" />}
                </span>
              ))}
            </div>
          )}

          {/* Anomalier — de udefinerede fejl Centralen fangede uden for sine nerver */}
          {(anomCounts.total ?? 0) > 0 && (
            <div className="central-anom">
              <div className="central-anom-head">
                <span>⚠ Udefinerede fejl</span>
                <span className="central-anom-badges">
                  {(anomCounts.critical ?? 0) > 0 && <span className="central-badge is-red">{anomCounts.critical} kritisk</span>}
                  {(anomCounts.high ?? 0) > 0 && <span className="central-badge is-yellow">{anomCounts.high} høj</span>}
                  <span className="central-anom-total">{anomCounts.total} i alt</span>
                </span>
              </div>
              <ul className="central-anom-list">
                {anomRecent.slice(0, 4).map((a) => (
                  <li key={a.signature} className={`central-anom-row imp-${a.importance}`} title={a.sample}>
                    <span className="central-anom-cat">{a.category}</span>
                    <span className="central-anom-cnt">×{a.count}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Lag 3 — flag (kun når der er noget) */}
          {(breakers.length > 0 || incidents.length > 0 || drift) && (
            <ul className="central-flags">
              {breakers.map((b) => (
                <li key={`brk-${b}`} className="central-flag is-red">
                  <ShieldAlert size={12} /> breaker åben: {b}
                </li>
              ))}
              {drift && (
                <li className="central-flag is-yellow">
                  <Zap size={12} /> config-drift: port {String(drift.declared_port)}≠{String(drift.actual_port)}
                </li>
              )}
              {incidents.slice(0, 4).map((i, n) => (
                <li key={`inc-${n}`} className={`central-flag ${i.severity === 'severe' ? 'is-red' : 'is-yellow'}`}
                  title={i.message}>
                  {i.cluster}/{i.nerve}: {i.message}
                </li>
              ))}
              {incidents.length > 4 && (
                <li className="central-flag is-muted">+{incidents.length - 4} flere incidents</li>
              )}
            </ul>
          )}

          {/* Lag 2 — live feed (det levende vindue) */}
          <div className="central-feed-head">Live nerve-fyringer</div>
          <ul className="central-feed">
            {feed.length === 0 && <li className="central-feed-empty">— stille —</li>}
            {feed.map((f, n) => (
              <li key={`feed-${n}`} className="central-feed-row central-feed-clickable"
                onClick={() => openNerve(f.nerve)} title="Klik → spor + lokation">
                <span className={`central-verdict central-v-${f.decision || f.kind}`} />
                <span className="central-feed-nerve">
                  {f.security && <span className="central-lock" title="sikkerheds-cluster">🔒</span>}
                  {f.cluster}/<b>{f.nerve}</b>
                </span>
                <span className="central-feed-kind">{f.decision || f.kind}</span>
              </li>
            ))}
          </ul>

          {/* Lag 4 — læring (foldbart) */}
          <button type="button" className="central-learn-toggle" onClick={() => setShowLearning((s) => !s)}>
            <Brain size={12} /> Læring {showLearning ? '▾' : '▸'}
            {typeof learn.proposals === 'number' && learn.proposals > 0 && (
              <span className="central-badge">{learn.proposals}</span>
            )}
          </button>
          {showLearning && (
            <div className="central-learn">
              <div className="central-learn-row">
                <span>Autonomi</span>
                <span className={`central-autonomy-${learn.autonomy || 'unknown'}`}
                  title={learn.autonomy_reason}>{learn.autonomy ?? '—'}</span>
              </div>
              {(learn.degrading ?? []).length > 0 && (
                <div className="central-learn-row">
                  <span>Degraderer</span>
                  <span>{(learn.degrading ?? []).map((d) => d.target).join(', ')}</span>
                </div>
              )}
              {(learn.root_causes ?? []).length > 0 && (
                <div className="central-learn-row">
                  <span>Rod-årsager</span>
                  <span>{(learn.root_causes ?? []).map((g) => `${g.target}×${g.count}`).join(', ')}</span>
                </div>
              )}
            </div>
          )}

          {/* Lag 5 — nerve-detalje (spor + lokation + tænd/sluk) */}
          {detail && (
            <div className="central-detail">
              <div className="central-detail-head">
                <span>{detail.security && '🔒 '}{detail.cluster}/<b>{detail.nerve}</b></span>
                <button type="button" className="central-detail-close" aria-label="luk"
                  onClick={() => setDetail(null)}><X size={13} /></button>
              </div>
              {detail.location && <div className="central-detail-loc" title={detail.location}>{detail.location}</div>}
              <div className="central-detail-toggle">
                <span className={detail.enabled ? 'is-on' : 'is-off'}>
                  {detail.enabled ? 'aktiv' : 'slået fra'}
                </span>
                {!detail.security ? (
                  <button type="button" onClick={() => doToggle(detail.nerve, !detail.enabled)}>
                    {detail.enabled ? 'Sluk' : 'Tænd'}
                  </button>
                ) : (
                  <span className="central-detail-locked" title="sikkerheds-nerve kan ikke slås fra">låst 🔒</span>
                )}
              </div>
              <div className="central-detail-feed-head">Seneste spor ({detail.recent.length})</div>
              <ul className="central-detail-feed">
                {detail.recent.length === 0 && <li className="central-feed-empty">— intet spor i bufferen —</li>}
                {detail.recent.map((r, n) => (
                  <li key={`d-${n}`} className="central-feed-row">
                    <span className={`central-verdict central-v-${r.decision || r.kind}`} />
                    <span className="central-feed-kind">{r.decision || r.kind}</span>
                    <span className="central-detail-reason" title={r.reason}>{r.reason || r.run_id || '—'}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </aside>
  )
}
