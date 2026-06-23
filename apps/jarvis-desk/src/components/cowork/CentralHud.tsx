import { useEffect, useRef, useState } from 'react'
import type { ApiConfig, CentralFeedItem, CentralProvider } from '../../lib/api'
import { getCentralRealtime, getCentralProviders, runCentralCommand } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'

/** Central — owner-terminalen ind i Den Intelligente Central (JARVIS-HUD, design 1:1 fra
 *  docs/design/jarvis-mind-design-tokens.md). Realtime: SSE-puls + snapshot-poll (kun mens
 *  åben). Bærer en LIVE command-line. Bjørn 2026-06-23: "jeg skal kunne se alt og styre alt
 *  i den terminal." Egen zone i cowork (adskilt fra Jarvis Mind). */
export function CentralHud({ config }: { config?: ApiConfig }) {
  const { data: snap } = usePollWhenVisible(() => getCentralRealtime(config!), 5000, !!config)
  const { data: prov } = usePollWhenVisible(() => getCentralProviders(config!), 15000, !!config)

  const [feed, setFeed] = useState<CentralFeedItem[]>([])
  const [live, setLive] = useState(false)
  useEffect(() => {
    if (!config) return
    setLive(true)
    const unsub = subscribeCentralStream(config,
      (it) => setFeed((f) => [it, ...f].slice(0, 7)), () => setLive(false))
    return () => { unsub(); setLive(false) }
  }, [config])

  const cov = snap?.coverage ?? {}
  const status = snap?.status ?? 'green'
  const clusters = snap?.clusters ?? []
  const incidents = snap?.incidents ?? []
  const anomalies = snap?.anomalies?.counts ?? {}
  const processes = snap?.processes ?? []
  const procOk = processes.filter((p: { degraded?: boolean }) => !p.degraded).length
  const dry = prov?.dry_cheap ?? []
  const provOk = (prov?.providers ?? []).filter((p) => p.ok).length

  return (
    <div className="central-hud">
      <div className="ch-scan" />
      <header className="ch-head">
        <div className="ch-title">
          <span className={`ch-dot ${live ? 'on' : ''}`} />
          <span className="ch-name">C E N T R A L</span>
          <span className="ch-owner">OWNER</span>
        </div>
        <div className="ch-headr">
          <Clock />
          <span className={`ch-stat tone-${status}`}>● {status === 'green' ? 'systemet lever' : status === 'yellow' ? 'overvåger' : 'kritisk'}</span>
        </div>
      </header>

      <div className="ch-top">
        <div className="ch-core">
          <div className={`ch-ring tone-${status}`}><span>{cov.nerves ?? '—'}</span></div>
          <div className="ch-corel">NERVER AKTIVE</div>
          <div className={`ch-cores tone-${status}`}>status: {status === 'green' ? 'nominel' : status}</div>
        </div>
        <div className="ch-metrics">
          <Metric n={cov.clusters} l="clusters" />
          <Metric n={`${procOk}/${processes.length || 2}`} l="processer" tone="green" />
          <Metric n={incidents.length} l="flag" tone={incidents.length ? 'amber' : undefined} />
          <Metric n={cov.nerves ? 70 : '—'} l="sind-felter" />
          <Metric n={`${provOk}/${prov?.providers?.length ?? 0}`} l="providers" tone="green" />
          <Metric n={dry.length} l="tørre lanes" tone={dry.length ? 'dry' : undefined} />
          <Metric n={snap?.open_breakers?.length ?? 0} l="breakers" tone={(snap?.open_breakers?.length ?? 0) ? 'red' : undefined} />
          <Metric n={anomalies.total ?? 0} l="anomalier" tone={(anomalies.total ?? 0) ? 'amber' : undefined} />
        </div>
      </div>

      <div className="ch-label">CLUSTER-KONSTELLATION</div>
      <div className="ch-clusters">
        {clusters.map((c) => (
          <div key={c.cluster} className={`ch-cl ${c.security ? 'sec' : `s-${c.status}`}`} title={c.cluster + (c.security ? ' 🔒' : '')}>{c.cluster}</div>
        ))}
      </div>

      <div className="ch-mid">
        <div className="ch-panel">
          <div className="ch-plabel"><span>LEVENDE NERVE-FEED</span><span className="ch-rt">● realtime</span></div>
          <div className="ch-feed">
            {feed.length === 0 && <div className="ch-dim">{live ? 'lytter på nervesystemet…' : 'forbinder…'}</div>}
            {feed.map((f, i) => (
              <div key={i} className="ch-frow">
                <span className={`ch-fd tone-${f.decision === 'red' ? 'red' : f.decision === 'yellow' ? 'amber' : 'green'}`} />
                <b>{f.cluster}</b><span className="ch-sep">/</span>{f.nerve}
                <span className="ch-dim"> {f.decision || f.kind}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="ch-side">
          <div className="ch-panel">
            <div className="ch-plabel">PROVIDERS</div>
            <div className="ch-prov">
              {(prov?.providers ?? []).slice(0, 8).map((p: CentralProvider) => (
                <div key={p.provider} className="ch-prow">
                  <span className={`ch-fd tone-${p.ok ? 'green' : p.degraded ? 'amber' : 'red'}`} />{p.provider}
                  <span className="ch-dim">{p.ok ? `${p.latency_ms}ms` : 'nede'}</span>
                </div>
              ))}
              {dry.length > 0 && <div className="ch-dry">tørre: {dry.join(', ')}</div>}
            </div>
          </div>
          {incidents.length > 0 && (
            <div className="ch-panel ch-flag">
              <div className="ch-plabel" style={{ color: '#f5a14a' }}>FLAG</div>
              {incidents.slice(0, 3).map((it, i) => (
                <div key={i} className="ch-flagrow">{it.nerve}: {(it.message || '').slice(0, 60)}</div>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="ch-label">BETJENING</div>
      <div className="ch-ctrl">
        <CtrlBtn config={config} cmd="status" icon="ti-activity" label="status" />
        <CtrlBtn config={config} cmd="incidents" icon="ti-flag" label="flag" />
        <CtrlBtn config={config} cmd="scan" icon="ti-radar-2" label="kør scan" />
        <CtrlBtn config={config} cmd="providers" icon="ti-server-cog" label="providers" />
        <CtrlBtn config={config} cmd="clusters" icon="ti-grid-dots" label="clusters" />
        <CtrlBtn config={config} cmd="breakers" icon="ti-bolt" label="breakers" />
      </div>

      <Terminal config={config} />

      <div className="ch-label">SIND — indre liv</div>
      <div className="ch-mind">
        {Array.from({ length: 70 }).map((_, i) => (
          <span key={i} className={`ch-cell ${i % 7 !== 0 && i % 5 !== 0 ? 'on' : ''}`}
            style={{ animationDelay: `${(i % 9) * 0.3}s` }} />
        ))}
      </div>
    </div>
  )
}

function Metric({ n, l, tone }: { n: unknown; l: string; tone?: string }) {
  return <div className="ch-m"><div className={`ch-mn ${tone ? `tone-${tone}` : ''}`}>{String(n ?? '—')}</div><div className="ch-ml">{l}</div></div>
}

function Clock() {
  const [t, setT] = useState('--:--:--')
  useEffect(() => { const id = setInterval(() => setT(new Date().toLocaleTimeString('da-DK')), 1000); return () => clearInterval(id) }, [])
  return <span className="ch-clock">{t}</span>
}

function CtrlBtn({ config, cmd, icon, label }: { config?: ApiConfig; cmd: string; icon: string; label: string }) {
  const [busy, setBusy] = useState(false)
  return (
    <button type="button" className={`ch-btn ${busy ? 'busy' : ''}`} disabled={!config || busy}
      onClick={async () => {
        if (!config) return
        setBusy(true)
        try { await runCentralCommand(config, cmd); window.dispatchEvent(new CustomEvent('central-cmd', { detail: cmd })) } catch { /* ignore */ }
        setTimeout(() => setBusy(false), 350)
      }}>
      <i className={`ti ${icon}`} aria-hidden="true" /> {label}
    </button>
  )
}

function Terminal({ config }: { config?: ApiConfig }) {
  const [log, setLog] = useState<{ cmd: string; lines: string[]; ok: boolean }[]>([])
  const [val, setVal] = useState('')
  const [hist, setHist] = useState<string[]>([])
  const [hi, setHi] = useState(-1)
  const endRef = useRef<HTMLDivElement>(null)
  useEffect(() => { try { endRef.current?.scrollIntoView?.({ block: 'end' }) } catch { /* jsdom */ } }, [log])

  const run = async (line: string) => {
    if (!config || !line.trim()) return
    setHist((h) => [line, ...h].slice(0, 40)); setHi(-1)
    try {
      const r = await runCentralCommand(config, line)
      setLog((l) => [...l, { cmd: line, lines: r.lines, ok: r.ok }].slice(-30))
    } catch (e) {
      setLog((l) => [...l, { cmd: line, lines: [`! ${e instanceof Error ? e.message : 'fejl'}`], ok: false }].slice(-30))
    }
  }
  useEffect(() => {
    const h = (e: Event) => { const d = (e as CustomEvent).detail as string; void run(d) }
    window.addEventListener('central-cmd', h)
    return () => window.removeEventListener('central-cmd', h)
  })

  return (
    <div className="ch-term">
      <div className="ch-plabel"><span>TERMINAL</span><span className="ch-dim">skriv 'help'</span></div>
      <div className="ch-termlog">
        {log.length === 0 && <div className="ch-dim">$ klar — skriv en kommando…</div>}
        {log.map((e, i) => (
          <div key={i}>
            <div className="ch-termcmd">$ {e.cmd}</div>
            {e.lines.map((ln, j) => <div key={j} className={ln.startsWith('!') ? 'ch-termerr' : 'ch-termout'}>{ln}</div>)}
          </div>
        ))}
        <div ref={endRef} />
      </div>
      <div className="ch-terminput">
        <span className="ch-prompt">$</span>
        <input value={val} placeholder="status · incidents · trace truth · toggle <nerve> off · scan · providers · help"
          onChange={(e) => setVal(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter') { void run(val); setVal('') }
            else if (e.key === 'ArrowUp') { e.preventDefault(); const n = Math.min(hi + 1, hist.length - 1); if (n >= 0) { setHi(n); setVal(hist[n] ?? '') } }
            else if (e.key === 'ArrowDown') { e.preventDefault(); const n = hi - 1; setHi(n); setVal(n >= 0 ? (hist[n] ?? '') : '') }
          }} />
      </div>
    </div>
  )
}
