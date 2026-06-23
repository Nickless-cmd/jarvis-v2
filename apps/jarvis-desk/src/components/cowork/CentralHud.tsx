import { useEffect, useRef, useState, type ReactNode } from 'react'
import { ToggleLeft, CheckCheck, Radar, ServerCog, RefreshCw, Zap, Flag, TerminalSquare, Stethoscope, ChevronDown, ChevronRight, type LucideIcon } from 'lucide-react'
import type { ApiConfig, CentralFeedItem, CentralProvider } from '../../lib/api'
import { getCentralRealtime, getCentralProviders, getCentralDiagnostics, getCentralNerve, runCentralCommand } from '../../lib/api'
import type { CentralDiagnostics } from '../../lib/api'
import { subscribeCentralStream } from '../../lib/centralStream'
import { usePollWhenVisible } from '../../hooks/usePollWhenVisible'

/** Central — owner-terminalen ind i Den Intelligente Central (JARVIS-HUD, design 1:1 fra
 *  docs/design/jarvis-mind-design-tokens.md). Realtime: SSE-puls + snapshot-poll (kun mens
 *  åben). Bærer en LIVE command-line. Bjørn 2026-06-23: "jeg skal kunne se alt og styre alt
 *  i den terminal." Egen zone i cowork (adskilt fra Jarvis Mind). */
export function CentralHud({ config }: { config?: ApiConfig }) {
  const { data: snap } = usePollWhenVisible(() => getCentralRealtime(config!), 5000, !!config)
  const { data: prov } = usePollWhenVisible(() => getCentralProviders(config!), 15000, !!config)

  const [live, setLive] = useState(false)

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

      <ClusterGrid clusters={clusters} />


      <div className="ch-mid">
        <FeedPanel config={config} onLive={setLive} />
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
          <div className={`ch-panel ${incidents.length ? 'ch-flag' : ''}`}>
            <div className="ch-plabel" style={{ color: incidents.length ? '#f5a14a' : '#6b8295' }}>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}><Flag size={13} aria-hidden="true" /> FLAG</span>
              <span className={incidents.length ? 'ch-flagcount' : 'ch-dim'}>{incidents.length}</span>
            </div>
            {incidents.length === 0
              ? <div className="ch-dim" style={{ fontSize: '12px' }}>ingen uløste flag</div>
              : incidents.slice(0, 4).map((it, i) => (
                  <div key={i} className="ch-flagrow"><b>{it.nerve}</b> {(it.message || '').slice(0, 54)}</div>
                ))}
          </div>
        </div>
      </div>

      <div className="ch-label">BETJENING — DU STYRER ALT HERFRA</div>
      <div className="ch-ctrl">
        <CtrlBtn config={config} prefill="toggle " Icon={ToggleLeft} label="tænd/sluk nerve" />
        <CtrlBtn config={config} cmd="resolve" Icon={CheckCheck} label="resolve flag" />
        <CtrlBtn config={config} cmd="scan" Icon={Radar} label="kør scan" />
        <CtrlBtn config={config} cmd="providers" Icon={ServerCog} label="provider-styring" />
        <CtrlBtn config={config} cmd="model" Icon={RefreshCw} label="model-skift" />
        <CtrlBtn config={config} cmd="daemons" Icon={Zap} label="daemon-kontrol" />
      </div>

      <Console config={config} />

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

// Støj-nerver (ren telemetri/health) — skjules i 'vigtige'/'fejl' så feed'et viser MENING.
const FEED_NOISE = new Set([
  'central_self_probe', 'central_health', 'device_presence', 'endpoint_call', 'cognitive_surface',
  'tool_usage_stats', 'endpoint_usage_stats', 'provider_health', 'census', 'learning', 'config_drift',
])

/** Isoleret feed: ejer sin egen state + stream (primitive deps → ingen drop-loop fra config-
 *  identitet), så de konstante fyringer kun re-renderer HER, ikke hele HUD'en. Klikbare rækker
 *  åbner fuld info i diagnostik. Støj filtreret; pause-på-hover. */
function FeedPanel({ config, onLive }: { config?: ApiConfig; onLive: (v: boolean) => void }) {
  const [feed, setFeed] = useState<CentralFeedItem[]>([])
  const [filter, setFilter] = useState<'vigtige' | 'fejl' | 'alle'>('vigtige')
  const pausedRef = useRef(false)
  const apiBaseUrl = config?.apiBaseUrl
  const authToken = config?.authToken
  useEffect(() => {
    if (!apiBaseUrl) return
    onLive(true)
    const cfg = { apiBaseUrl, authToken: authToken ?? null }
    const unsub = subscribeCentralStream(cfg,
      (it) => { if (!pausedRef.current) setFeed((f) => [it, ...f].slice(0, 200)) },
      () => onLive(false))
    return () => { unsub() }
  }, [apiBaseUrl, authToken, onLive])
  const shown = feed.filter((f) => {
    if (filter === 'alle') return true
    const isErr = f.kind === 'error' || f.decision === 'red'
    if (filter === 'fejl') return isErr || f.decision === 'yellow'
    // vigtige: ægte beslutninger + fejl, men IKKE støj-nerverne
    if (FEED_NOISE.has(f.nerve)) return isErr || f.decision === 'red' || f.decision === 'yellow'
    return isErr || f.decision === 'red' || f.decision === 'yellow' || f.kind === 'decide'
  }).slice(0, 50)
  return (
    <div className="ch-panel">
      <div className="ch-plabel">
        <span>NERVE-FEED <span className="ch-rt">● realtime</span></span>
        <span className="ch-ffilter">
          {(['vigtige', 'fejl', 'alle'] as const).map((m) => (
            <button key={m} type="button" className={`ch-fbtn ${filter === m ? 'on' : ''}`} onClick={() => setFilter(m)}>{m}</button>
          ))}
        </span>
      </div>
      <div className="ch-feed ch-scrolly"
        onMouseEnter={() => { pausedRef.current = true }} onMouseLeave={() => { pausedRef.current = false }}>
        {shown.length === 0 && <div className="ch-dim">{filter === 'alle' ? 'lytter på nervesystemet…' : 'intet vigtigt lige nu — alt nominelt (skift til ALLE for telemetri)'}</div>}
        {shown.map((f, i) => {
          const tone = f.kind === 'error' || f.decision === 'red' ? 'red'
            : f.decision === 'yellow' ? 'amber' : f.decision === 'green' ? 'green'
            : f.kind === 'decide' ? 'cyan' : 'dim'
          const verdict = f.kind === 'error' ? 'FEJL' : f.decision === 'red' ? 'HARD-BLOK'
            : f.decision === 'yellow' ? 'advar' : f.decision || f.kind
          return (
            <button type="button" key={i} className={`ch-frow tone-line-${tone}`}
              onClick={() => window.dispatchEvent(new CustomEvent('central-detail', { detail: f.nerve }))}
              title="klik for fuld info i diagnostik">
              <span className="ch-fcl">{f.cluster}</span><span className="ch-sep">/</span>
              <span className="ch-fnv">{f.nerve}</span>
              <span className={`ch-fval tone-${tone}`}>{verdict}</span>
              {f.run_id && <span className="ch-frun">#{f.run_id.slice(-6)}</span>}
              {f.reason && <div className="ch-freason">{f.reason}</div>}
            </button>
          )
        })}
      </div>
    </div>
  )
}

/** Cluster-konstellation — foldbar, starter sammenfoldet med smart resumé (røde/gule/sikkerhed
 *  fremhævet). Udfold for det fulde grid. */
function ClusterGrid({ clusters }: { clusters: { cluster: string; status: string; security: boolean }[] }) {
  const [open, setOpen] = useState(false)
  const red = clusters.filter((c) => c.status === 'red')
  const yellow = clusters.filter((c) => c.status === 'yellow')
  const sec = clusters.filter((c) => c.security)
  return (
    <div>
      <button type="button" className="ch-label ch-foldlabel" onClick={() => setOpen((o) => !o)}>
        {open ? <ChevronDown size={13} /> : <ChevronRight size={13} />} CLUSTER-KONSTELLATION
        <span className="ch-foldsum">
          {red.length > 0 && <span className="tone-red">{red.length} rød</span>}
          {yellow.length > 0 && <span className="tone-amber"> {yellow.length} gul</span>}
          {red.length === 0 && yellow.length === 0 && <span className="tone-green">{clusters.length} nominelle</span>}
          <span className="ch-dim"> · {sec.length} sikkerhed</span>
        </span>
      </button>
      {!open && (red.length > 0 || yellow.length > 0) && (
        <div className="ch-clusters" style={{ marginBottom: '12px' }}>
          {[...red, ...yellow].map((c) => (
            <div key={c.cluster} className={`ch-cl s-${c.status}`} title={c.cluster}>{c.cluster}</div>
          ))}
        </div>
      )}
      {open && (
        <div className="ch-clusters">
          {clusters.map((c) => (
            <div key={c.cluster} className={`ch-cl ${c.security ? 'sec' : `s-${c.status}`}`} title={c.cluster + (c.security ? ' 🔒' : '')}>{c.cluster}</div>
          ))}
        </div>
      )}
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

function CtrlBtn({ config, cmd, prefill, Icon, label }: { config?: ApiConfig; cmd?: string; prefill?: string; Icon: LucideIcon; label: string }) {
  const [busy, setBusy] = useState(false)
  return (
    <button type="button" className={`ch-btn ${busy ? 'busy' : ''}`} disabled={!config}
      onClick={() => {
        if (prefill) { window.dispatchEvent(new CustomEvent('central-prefill', { detail: prefill })); return }
        if (!cmd) return
        setBusy(true)
        window.dispatchEvent(new CustomEvent('central-cmd', { detail: cmd }))
        setTimeout(() => setBusy(false), 400)
      }}>
      <Icon size={14} aria-hidden="true" /> {label}
    </button>
  )
}

/** Konsol med mode-skift: Terminal (command-line) ↔ Diagnostik (fuldt debug-sted). */
function Console({ config }: { config?: ApiConfig }) {
  const [mode, setMode] = useState<'terminal' | 'diag'>('terminal')
  const [focus, setFocus] = useState<string>('')
  // Klik på en feed-række → åbn fuld info i diagnostik (fokus på den nerve).
  useEffect(() => {
    const h = (e: Event) => { setFocus((e as CustomEvent).detail as string); setMode('diag') }
    window.addEventListener('central-detail', h)
    return () => window.removeEventListener('central-detail', h)
  }, [])
  return (
    <div className="ch-console">
      <div className="ch-cnav">
        <button type="button" className={`ch-cnavb ${mode === 'terminal' ? 'on' : ''}`} onClick={() => setMode('terminal')}>
          <TerminalSquare size={14} aria-hidden="true" /> terminal
        </button>
        <button type="button" className={`ch-cnavb ${mode === 'diag' ? 'on' : ''}`} onClick={() => setMode('diag')}>
          <Stethoscope size={14} aria-hidden="true" /> diagnostik
        </button>
      </div>
      {mode === 'terminal' ? <Terminal config={config} /> : <Diagnostics config={config} focus={focus} onClearFocus={() => setFocus('')} />}
    </div>
  )
}

function Diagnostics({ config, focus, onClearFocus }: { config?: ApiConfig; focus?: string; onClearFocus?: () => void }) {
  const { data, loading } = usePollWhenVisible(() => getCentralDiagnostics(config!), 8000, !!config)
  const d: CentralDiagnostics | null = data
  if (!d) return <div className="ch-diag ch-dim">{loading ? 'henter diagnostik…' : 'ingen data'}</div>
  const sevTone = (s: string) => s === 'severe' ? 'red' : s === 'error' ? 'amber' : 'cyan'
  const impTone = (s: string) => s === 'critical' || s === 'high' ? 'red' : s === 'medium' ? 'amber' : 'cyan'
  return (
    <div className="ch-diag ch-scrolly">
      {focus && <NerveFocus config={config} nerve={focus} onClose={onClearFocus} />}
      <DSec n={d.incidents.length} label="ULØSTE FLAG">
        {d.incidents.map((it, i) => (
          <div key={i} className="ch-drow">
            <span className={`ch-dtag tone-${sevTone(it.severity)}`}>{it.severity}</span>
            <b>{it.cluster}/{it.nerve}</b> <span className="ch-dim">{(it.ts || '').slice(11, 19)}</span>
            <div className="ch-dmsg">{it.message}</div>
          </div>
        ))}
      </DSec>
      <DSec n={d.anomalies.length} label="UDEFINEREDE FEJL (anomalier)">
        {d.anomalies.map((a, i) => (
          <div key={i} className="ch-drow">
            <span className={`ch-dtag tone-${impTone(a.importance)}`}>{a.importance}</span>
            <span className="ch-dim">×{a.count} {a.category}</span>
            {a.location && <span className="ch-dloc">{a.location}</span>}
            <div className="ch-dmsg">{a.sample}</div>
          </div>
        ))}
      </DSec>
      <DSec n={d.instrument.length} label="SILENT-FAILURE-FUND (top)">
        {d.instrument.map((f, i) => (
          <div key={i} className="ch-drow">
            <span className={`ch-dtag tone-${f.severity === 'critical' ? 'red' : 'amber'}`}>{f.score}</span>
            <b>{f.kind}</b> <span className="ch-dim">{f.file}:{f.line}</span>
            <div className="ch-dmsg">{f.snippet}</div>
          </div>
        ))}
      </DSec>
      {d.root_causes.length > 0 && (
        <DSec n={d.root_causes.length} label="ROD-ÅRSAGER (gentagne)">
          {d.root_causes.map((r, i) => <div key={i} className="ch-drow"><b>{r.cluster}/{r.nerve}</b> <span className="ch-dim">×{r.count}</span></div>)}
        </DSec>
      )}
    </div>
  )
}

/** Fuld info om ÉN nerve (åbnet ved klik i feed'et): lokation + on/off + seneste fyringer. */
function NerveFocus({ config, nerve, onClose }: { config?: ApiConfig; nerve: string; onClose?: () => void }) {
  const [d, setD] = useState<import('../../lib/api').CentralNerveDetail | null>(null)
  const [err, setErr] = useState('')
  useEffect(() => {
    if (!config || !nerve) return
    let alive = true
    getCentralNerve(config, nerve).then((r) => alive && setD(r)).catch((e) => alive && setErr(String(e)))
    return () => { alive = false }
  }, [config, nerve])
  return (
    <div className="ch-focus">
      <div className="ch-dlabel" style={{ display: 'flex', justifyContent: 'space-between' }}>
        <span>FOKUS: {nerve}</span>
        <button type="button" className="ch-fbtn" onClick={onClose}>luk</button>
      </div>
      {err && <div className="ch-dmsg tone-red">{err}</div>}
      {d && (
        <>
          <div className="ch-drow">
            <b>{d.cluster}/{d.nerve}</b> {d.security && <span className="ch-dtag tone-red">🔒 sikkerhed</span>}
            <span className={`ch-dtag tone-${d.enabled ? 'cyan' : 'amber'}`}>{d.enabled ? 'aktiv' : 'slået fra'}</span>
            {d.location && <div className="ch-dloc">{d.location}</div>}
          </div>
          <div className="ch-dlabel" style={{ marginTop: '8px' }}>SENESTE FYRINGER</div>
          {(d.recent ?? []).slice(0, 12).map((r, i) => (
            <div key={i} className="ch-drow" style={{ fontSize: '12px' }}>
              <span className={`ch-fval tone-${r.decision === 'red' ? 'red' : r.decision === 'yellow' ? 'amber' : 'green'}`}>{r.decision || r.kind}</span>
              {r.reason && <span className="ch-dim"> {r.reason}</span>}
              {r.run_id && <span className="ch-frun">#{r.run_id.slice(-6)}</span>}
            </div>
          ))}
          {(d.recent ?? []).length === 0 && <div className="ch-dim" style={{ fontSize: '12px' }}>ingen nylige fyringer i bufferen</div>}
        </>
      )}
    </div>
  )
}

function DSec({ n, label, children }: { n: number; label: string; children: ReactNode }) {
  return (
    <div className="ch-dsec">
      <div className="ch-dlabel">{label} <span className={n ? 'ch-flagcount' : 'ch-dim'}>{n}</span></div>
      {n === 0 ? <div className="ch-dim" style={{ fontSize: '12px', padding: '2px 0 6px' }}>ingen</div> : children}
    </div>
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
  const inputRef = useRef<HTMLInputElement>(null)
  useEffect(() => {
    const h = (e: Event) => { const d = (e as CustomEvent).detail as string; void run(d) }
    const p = (e: Event) => { setVal((e as CustomEvent).detail as string); inputRef.current?.focus?.() }
    window.addEventListener('central-cmd', h)
    window.addEventListener('central-prefill', p)
    return () => { window.removeEventListener('central-cmd', h); window.removeEventListener('central-prefill', p) }
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
        <input ref={inputRef} value={val} placeholder="status · incidents · trace truth · toggle <nerve> off · scan · providers · help"
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
