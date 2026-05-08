import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Brain, CircleDot, Compass, Eye, GitBranch, RefreshCcw, Route, Zap } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'

const STATUS_COLOR = {
  connected: T.green,
  experimental: T.accent,
  partial: T.amber,
  missing: T.red,
  critical: T.red,
  active: T.accent,
  open: T.amber,
  done: T.green,
  'visible-surface': T.green,
  'partial-surface': T.amber,
  'emerging-surface': T.accent,
}

function statusColor(status) {
  return STATUS_COLOR[String(status || '').toLowerCase()] || T.text3
}

function StatusPill({ status }) {
  const color = statusColor(status)
  return (
    <span style={s({
      ...mono,
      display: 'inline-flex',
      alignItems: 'center',
      gap: 4,
      padding: '2px 7px',
      borderRadius: 8,
      border: `1px solid ${color}44`,
      background: `${color}18`,
      color,
      fontSize: 9,
      textTransform: 'uppercase',
    })}>
      <CircleDot size={8} />
      {status || 'unknown'}
    </span>
  )
}

function SummaryCard({ icon: Icon, label, value, color = T.text1 }) {
  return (
    <article style={s({
      background: T.bgRaised,
      border: `1px solid ${T.border0}`,
      borderRadius: T.r_sm,
      padding: 12,
      minHeight: 76,
      display: 'flex',
      flexDirection: 'column',
      gap: 6,
    })}>
      <span style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em', display: 'flex', alignItems: 'center', gap: 6 })}>
        <Icon size={12} />
        {label}
      </span>
      <strong style={s({ color, fontSize: 18, lineHeight: 1 })}>{value}</strong>
    </article>
  )
}

function NodeCard({ node }) {
  return (
    <article style={s({
      background: T.bgRaised,
      border: `1px solid ${node.state === 'experimental' ? `${T.accent}55` : T.border0}`,
      borderRadius: T.r_sm,
      padding: 12,
      minWidth: 0,
    })}>
      <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 8, alignItems: 'flex-start', marginBottom: 6 })}>
        <div style={s({ minWidth: 0 })}>
          <strong style={s({ display: 'block', fontSize: 13, color: T.text1 })}>{node.label}</strong>
          <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>{node.kind}</span>
        </div>
        <StatusPill status={node.state} />
      </div>
      <p style={s({ margin: 0, color: T.text2, fontSize: 11, lineHeight: 1.45 })}>{node.summary}</p>
      <div style={s({ ...mono, marginTop: 8, color: T.text3, fontSize: 9, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
        {node.surface}
      </div>
    </article>
  )
}

function BridgeRow({ bridge, nodeLabelById }) {
  const color = statusColor(bridge.status)
  return (
    <div style={s({
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 0.9fr) 22px minmax(0, 0.9fr) minmax(0, 1.6fr) auto',
      gap: 8,
      alignItems: 'center',
      padding: '9px 10px',
      borderRadius: T.r_sm,
      border: `1px solid ${T.border0}`,
      background: T.bgRaised,
    })}>
      <strong style={s({ fontSize: 11, color: T.text1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' })}>
        {nodeLabelById.get(bridge.source) || bridge.source}
      </strong>
      <ArrowRight size={13} color={color} />
      <strong style={s({ fontSize: 11, color: T.text1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis' })}>
        {nodeLabelById.get(bridge.target) || bridge.target}
      </strong>
      <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.35, minWidth: 0, wordBreak: 'break-word' })}>{bridge.summary}</span>
      <StatusPill status={bridge.status} />
    </div>
  )
}

function QuestionRow({ item }) {
  return (
    <article style={s({
      background: T.bgRaised,
      border: `1px solid ${T.border0}`,
      borderRadius: T.r_sm,
      padding: 12,
    })}>
      <div style={s({ display: 'flex', justifyContent: 'space-between', gap: 10, marginBottom: 6 })}>
        <strong style={s({ fontSize: 12, color: T.text1 })}>{item.question}</strong>
        <StatusPill status={item.status} />
      </div>
      <p style={s({ margin: 0, color: T.text2, fontSize: 11, lineHeight: 1.45 })}>{item.answer}</p>
    </article>
  )
}

function DarkEdgeRow({ item }) {
  const evidence = Array.isArray(item.evidence) ? item.evidence : []
  return (
    <article style={s({
      background: T.bgRaised,
      border: `1px solid ${T.border0}`,
      borderRadius: T.r_sm,
      padding: 12,
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 0.8fr) minmax(0, 1.4fr) minmax(0, 0.7fr) auto',
      gap: 10,
      alignItems: 'center',
    })}>
      <strong style={s({ fontSize: 11, color: T.text1, minWidth: 0, wordBreak: 'break-word' })}>
        {item.source} → {item.target}
      </strong>
      <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
        {item.summary}
        {evidence.length > 0 ? (
          <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
            evidence {evidence.length} · {item.remaining_gap || 'no remaining gap noted'}
          </span>
        ) : null}
      </span>
      <span style={s({ ...mono, color: T.text3, fontSize: 9, minWidth: 0, wordBreak: 'break-word' })}>{item.surface}</span>
      <StatusPill status={item.visibility} />
    </article>
  )
}

function RepairBriefRow({ item }) {
  const edge = item.edge || {}
  const files = Array.isArray(item.suggested_files) ? item.suggested_files : []
  return (
    <article style={s({
      background: T.bgRaised,
      border: `1px solid ${T.border0}`,
      borderRadius: T.r_sm,
      padding: 12,
      display: 'grid',
      gridTemplateColumns: 'minmax(0, 0.8fr) minmax(0, 1.4fr) minmax(0, 0.8fr) auto',
      gap: 10,
      alignItems: 'center',
    })}>
      <div style={s({ minWidth: 0 })}>
        <strong style={s({ display: 'block', fontSize: 12, color: T.text1, minWidth: 0, wordBreak: 'break-word' })}>
          {edge.title || item.scope || item.task_id}
        </strong>
        <span style={s({ ...mono, color: T.text3, fontSize: 9 })}>{item.task_id}</span>
      </div>
      <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
        {item.recommended_next_action || item.goal}
      </span>
      <span style={s({ ...mono, color: T.text3, fontSize: 9, minWidth: 0, wordBreak: 'break-word' })}>
        {files.slice(0, 3).join(' · ')}
      </span>
      <StatusPill status={item.status || 'open'} />
    </article>
  )
}

export function AgencyMapTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function load() {
    setError('')
    try {
      const result = await backend.getMissionControlAgencyMap()
      setData(result)
    } catch (exc) {
      setError(String(exc?.message || exc))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    let cancelled = false
    async function loadOnce() {
      setError('')
      try {
        const result = await backend.getMissionControlAgencyMap()
        if (!cancelled) setData(result)
      } catch (exc) {
        if (!cancelled) setError(String(exc?.message || exc))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    loadOnce()
    const interval = setInterval(loadOnce, 60000)
    return () => { cancelled = true; clearInterval(interval) }
  }, [])

  const nodeLabelById = useMemo(() => {
    return new Map((data?.nodes || []).map((node) => [node.id, node.label]))
  }, [data])

  if (loading) {
    return <div style={s({ padding: 24, color: T.text3, ...mono, fontSize: 11 })}>Loading Agency Map...</div>
  }

  if (error) {
    return <div style={s({ padding: 24, color: T.red, ...mono, fontSize: 11 })}>{error}</div>
  }

  const summary = data?.summary || {}
  const bridges = data?.bridges || []
  const cartographer = data?.cartographer || {}
  const cartSummary = cartographer.summary || {}
  const recommended = cartographer.recommendedNextTask || data?.recommendedNextTask || null
  const autoTask = cartographer.autoTask || {}
  const systemCartographer = data?.systemCartographer || {}
  const systemSummary = systemCartographer.summary || {}
  const observabilityTask = systemCartographer.recommendedObservabilityTask || null
  const systemHealth = systemCartographer.systemHealth || {}
  const systemAutoTask = systemCartographer.autoTask || {}
  const theaterAudit = systemCartographer.theaterAudit || {}
  const theaterSummary = theaterAudit.summary || {}
  const theaterTask = theaterAudit.recommendedTheaterTask || systemHealth.recommended_theater_refactor || null

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 12, padding: '16px 20px' })}>
      <div style={s({ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 })}>
        <div>
          <h2 style={s({ margin: 0, fontSize: 16, fontWeight: 600, color: T.text1, display: 'flex', alignItems: 'center', gap: 8 })}>
            <Route size={16} color={T.accent} />
            Agency Map
          </h2>
          <p style={s({ margin: '4px 0 0', color: T.text3, fontSize: 11 })}>
            Senses, emotion, memory, goals, repair, executive choice, tools, and MC visibility.
          </p>
        </div>
        <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
          <span style={s({ ...mono, color: T.text3, fontSize: 9 })}>{formatFreshness(data?.fetchedAt)}</span>
          <button
            onClick={load}
            title="Refresh Agency Map"
            style={s({
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: 30,
              height: 30,
              borderRadius: 8,
              border: `1px solid ${T.border1}`,
              background: T.glass,
              color: T.text2,
              cursor: 'pointer',
            })}
          >
            <RefreshCcw size={13} />
          </button>
        </div>
      </div>

      <section style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: 8 })}>
        <SummaryCard icon={Brain} label="Nodes" value={summary.nodes || 0} />
        <SummaryCard icon={GitBranch} label="Connected" value={summary.connected || 0} color={T.green} />
        <SummaryCard icon={Compass} label="Partial" value={summary.partial || 0} color={T.amber} />
        <SummaryCard icon={Zap} label="Experimental" value={summary.experimental || 0} color={T.accent} />
        <SummaryCard icon={Eye} label="Missing" value={summary.missing || 0} color={T.red} />
        <SummaryCard icon={Eye} label="Dark Edges" value={summary.dark_edges || 0} color={T.amber} />
      </section>

      <section style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 8 })}>
        {(data?.nodes || []).map((node) => <NodeCard key={node.id} node={node} />)}
      </section>

      <section style={s({ display: 'flex', flexDirection: 'column', gap: 7 })}>
        <div style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
          Bridges
        </div>
        {bridges.map((bridge, index) => (
          <BridgeRow
            key={`${bridge.source}-${bridge.target}-${index}`}
            bridge={bridge}
            nodeLabelById={nodeLabelById}
          />
        ))}
      </section>

      <section style={s({ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 8 })}>
        {(data?.questions || []).map((item) => <QuestionRow key={item.question} item={item} />)}
      </section>

      <section style={s({
        background: T.bgRaised,
        border: `1px solid ${T.border0}`,
        borderRadius: T.r_sm,
        padding: 12,
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 0.7fr) minmax(0, 1.3fr) auto',
        gap: 10,
        alignItems: 'center',
      })}>
        <strong style={s({ fontSize: 12, color: T.text1 })}>Agency Cartographer</strong>
        <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4 })}>
          scanned {cartSummary.vision_edges || 0} vision edges · connected {cartSummary.connected || 0} · partial {cartSummary.partial || 0} · missing {cartSummary.missing || 0}
          {autoTask.status ? (
            <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
              auto-task {autoTask.status}{autoTask.task_id ? ` · ${autoTask.task_id}` : ''}
            </span>
          ) : null}
        </span>
        <span style={s({ ...mono, color: T.text3, fontSize: 9 })}>{formatFreshness(cartographer.scannedAt)}</span>
      </section>

      <section style={s({
        background: T.bgRaised,
        border: `1px solid ${T.border0}`,
        borderRadius: T.r_sm,
        padding: 12,
        display: 'grid',
        gridTemplateColumns: 'minmax(0, 0.8fr) minmax(0, 1.4fr) auto',
        gap: 10,
        alignItems: 'center',
      })}>
        <strong style={s({ fontSize: 12, color: T.text1 })}>System Cartographer</strong>
        <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4 })}>
          services {systemSummary.services || 0} · daemons {systemSummary.daemons || 0} · surfaces {systemSummary.surfaces || 0} · events {systemSummary.event_families || 0} · dark {systemSummary.dark_edges || 0}
          <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
            observed events {systemSummary.observed_events || 0} · causal edges {systemSummary.observed_causal_edges || 0} · family edges {systemSummary.observed_causal_family_edges || 0}
          </span>
          <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
            coverage avg {systemSummary.avg_causal_coverage_score || 0} · low {systemSummary.low_coverage_services || 0} · auto-task {systemAutoTask.status || 'unknown'}
          </span>
          <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
            theater findings {systemSummary.theater_findings || 0} · high-risk {systemSummary.theater_high_risk || 0}
          </span>
        </span>
        <StatusPill status={systemCartographer.mode === 'system-cartographer-v1' ? 'active' : 'missing'} />
      </section>

      {systemHealth.summary ? (
        <section style={s({
          background: T.bgRaised,
          border: `1px solid ${T.border0}`,
          borderRadius: T.r_sm,
          padding: 12,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 0.8fr) minmax(0, 1.6fr) auto',
          gap: 10,
          alignItems: 'center',
        })}>
          <strong style={s({ fontSize: 12, color: T.text1 })}>System Health</strong>
          <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
            {systemHealth.summary}
          </span>
          <StatusPill status={systemHealth.state || 'unknown'} />
        </section>
      ) : null}

      {theaterAudit.mode ? (
        <section style={s({
          background: T.bgRaised,
          border: `1px solid ${T.border0}`,
          borderRadius: T.r_sm,
          padding: 12,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 0.8fr) minmax(0, 1.4fr) auto',
          gap: 10,
          alignItems: 'center',
        })}>
          <strong style={s({ fontSize: 12, color: T.text1 })}>Theater Audit</strong>
          <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
            findings {theaterSummary.findings || 0} · high {theaterSummary.high_risk || 0} · medium {theaterSummary.medium_risk || 0} · files {theaterSummary.files || 0}
            {theaterTask ? (
              <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
                next {theaterTask.scope} · score {theaterTask.priority_score || 0}
              </span>
            ) : null}
          </span>
          <StatusPill status={(theaterSummary.high_risk || 0) > 0 ? 'open' : 'done'} />
        </section>
      ) : null}

      {theaterTask ? (
        <section style={s({
          background: T.bgRaised,
          border: `1px solid ${statusColor(theaterTask.priority)}66`,
          borderRadius: T.r_sm,
          padding: 12,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 0.9fr) minmax(0, 1.4fr) minmax(0, 0.8fr) auto',
          gap: 10,
          alignItems: 'center',
        })}>
          <div style={s({ minWidth: 0 })}>
            <span style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
              Recommended theater refactor
            </span>
            <strong style={s({ display: 'block', marginTop: 4, fontSize: 13, color: T.text1, minWidth: 0, wordBreak: 'break-word' })}>
              {theaterTask.title}
            </strong>
          </div>
          <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
            {theaterTask.goal}
            {theaterTask.reason ? (
              <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
                {theaterTask.reason}
              </span>
            ) : null}
          </span>
          <span style={s({ ...mono, color: T.text3, fontSize: 9, minWidth: 0, wordBreak: 'break-word' })}>
            score {theaterTask.priority_score || 0} · {theaterTask.scope}
          </span>
          <StatusPill status={theaterTask.priority} />
        </section>
      ) : null}

      {observabilityTask ? (
        <section style={s({
          background: T.bgRaised,
          border: `1px solid ${statusColor(observabilityTask.priority)}66`,
          borderRadius: T.r_sm,
          padding: 12,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 0.9fr) minmax(0, 1.4fr) minmax(0, 0.8fr) auto',
          gap: 10,
          alignItems: 'center',
        })}>
          <div style={s({ minWidth: 0 })}>
            <span style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
              Recommended observability bridge
            </span>
            <strong style={s({ display: 'block', marginTop: 4, fontSize: 13, color: T.text1, minWidth: 0, wordBreak: 'break-word' })}>
              {observabilityTask.title}
            </strong>
          </div>
          <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
            {observabilityTask.goal}
            {observabilityTask.reason ? (
              <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
                {observabilityTask.reason}
              </span>
            ) : null}
          </span>
          <span style={s({ ...mono, color: T.text3, fontSize: 9, minWidth: 0, wordBreak: 'break-word' })}>
            score {observabilityTask.priority_score || 0} · {observabilityTask.scope}
          </span>
          <StatusPill status={observabilityTask.priority} />
        </section>
      ) : null}

      {recommended ? (
        <section style={s({
          background: T.bgRaised,
          border: `1px solid ${statusColor(recommended.priority)}66`,
          borderRadius: T.r_sm,
          padding: 12,
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 0.9fr) minmax(0, 1.4fr) minmax(0, 0.8fr) auto',
          gap: 10,
          alignItems: 'center',
        })}>
          <div style={s({ minWidth: 0 })}>
            <span style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
              Recommended next task
            </span>
            <strong style={s({ display: 'block', marginTop: 4, fontSize: 13, color: T.text1, minWidth: 0, wordBreak: 'break-word' })}>
              {recommended.title}
            </strong>
          </div>
          <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
            {recommended.goal || recommended.summary}
            {recommended.reason ? (
              <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
                {recommended.reason}
              </span>
            ) : null}
          </span>
          <span style={s({ ...mono, color: T.text3, fontSize: 9, minWidth: 0, wordBreak: 'break-word' })}>
            score {recommended.priority_score || 0} · {recommended.scope || recommended.target}
          </span>
          <StatusPill status={recommended.priority} />
        </section>
      ) : null}

      <section style={s({ display: 'flex', flexDirection: 'column', gap: 7 })}>
        <div style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
          Dark Edges
        </div>
        {(data?.darkEdges || []).map((item) => (
          <DarkEdgeRow key={`${item.source}-${item.target}`} item={item} />
        ))}
      </section>

      <section style={s({ display: 'flex', flexDirection: 'column', gap: 7 })}>
        <div style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
          Next Moves
        </div>
        {(data?.nextMoves || []).map((item) => (
          <article key={item.title} style={s({
            background: T.bgRaised,
            border: `1px solid ${T.border0}`,
            borderRadius: T.r_sm,
            padding: 12,
            display: 'grid',
            gridTemplateColumns: 'minmax(0, 0.8fr) minmax(0, 1.4fr) minmax(0, 0.6fr) auto',
            gap: 10,
            alignItems: 'center',
          })}>
            <strong style={s({ fontSize: 12, color: T.text1 })}>{item.title}</strong>
            <span style={s({ color: T.text2, fontSize: 11, lineHeight: 1.4, minWidth: 0, wordBreak: 'break-word' })}>
              {item.summary}
              {item.reason ? (
                <span style={s({ display: 'block', ...mono, color: T.text3, fontSize: 9, marginTop: 4 })}>
                  {item.reason}
                </span>
              ) : null}
            </span>
            <span style={s({ ...mono, color: T.text3, fontSize: 9, minWidth: 0, wordBreak: 'break-word' })}>{item.target}</span>
            <StatusPill status={item.priority} />
          </article>
        ))}
      </section>

      {(data?.repairBriefs || []).length > 0 ? (
        <section style={s({ display: 'flex', flexDirection: 'column', gap: 7 })}>
          <div style={s({ ...mono, color: T.text3, fontSize: 9, textTransform: 'uppercase', letterSpacing: '0.08em' })}>
            Repair Briefs
          </div>
          {(data?.repairBriefs || []).map((item) => (
            <RepairBriefRow key={item.task_id} item={item} />
          ))}
        </section>
      ) : null}
    </div>
  )
}
