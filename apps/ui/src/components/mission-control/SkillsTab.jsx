import { useEffect, useState } from 'react'
import { RefreshCcw, Wrench } from 'lucide-react'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, MetricCard, ScrollPanel, EmptyState, Skeleton } from './shared'
import { backend } from '../../lib/adapters'
import { formatFreshness } from './meta'

const WRITE_WORDS = ['write', 'delete', 'send', 'exec', 'create', 'remove', 'modify', 'update', 'post', 'put', 'patch']

function toolRisk(tool) {
  const n = tool.name.toLowerCase()
  if (tool.required && tool.required.length > 0) return 'write'
  if (WRITE_WORDS.some((w) => n.includes(w))) return 'write'
  return 'read'
}

function RiskChip({ tool }) {
  const risk = toolRisk(tool)
  const color = risk === 'write' ? T.amber : T.blue
  return (
    <span style={s({
      ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10,
      background: `${color}18`, border: `1px solid ${color}35`, color,
    })}>
      {risk}
    </span>
  )
}

export function SkillsTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [fetchedAt, setFetchedAt] = useState('')

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlSkills()
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
      const result = await backend.getMissionControlSkills()
      setData(result)
      setFetchedAt(new Date().toISOString())
    } finally {
      setLoading(false)
    }
  }

  const tools = data?.tools || []
  const filtered = search.trim()
    ? tools.filter((t) =>
        t.name.toLowerCase().includes(search.toLowerCase()) ||
        t.description.toLowerCase().includes(search.toLowerCase())
      )
    : tools

  const writeCount = tools.filter((t) => toolRisk(t) === 'write').length
  const readCount = tools.length - writeCount

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <Wrench size={15} color={T.accent} />
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Skills</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
          {fetchedAt ? formatFreshness(fetchedAt) : ''}
        </span>
        <button
          onClick={refresh}
          disabled={loading}
          style={s({ marginLeft: 'auto', padding: '4px 8px', borderRadius: 7, border: `1px solid ${T.border1}`, background: T.bgOverlay, color: T.text2, cursor: loading ? 'not-allowed' : 'pointer', opacity: loading ? 0.5 : 1 })}
        >
          <RefreshCcw size={11} />
        </button>
      </div>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Tools i alt" value={loading ? '…' : data?.total ?? 0} icon={Wrench} />
        <MetricCard label="Read-only" value={loading ? '…' : readCount} />
        <MetricCard label="Write/send" value={loading ? '…' : writeCount} color={writeCount > 0 ? T.amber : undefined} />
        <MetricCard label="Kald i dag" value={loading ? '…' : data?.calls_today ?? 0} />
      </div>

      <Card>
        <SectionTitle>Tooloversigt</SectionTitle>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Søg tools…"
          style={s({
            width: '100%', boxSizing: 'border-box', marginBottom: 10,
            padding: '6px 10px', borderRadius: 7, border: `1px solid ${T.border1}`,
            background: T.bgSurface, color: T.text1, ...mono, fontSize: 10,
          })}
        />
        {loading ? (
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={32} />)}
          </div>
        ) : filtered.length === 0 ? (
          <EmptyState title="Ingen tools matcher">Prøv en anden søgning.</EmptyState>
        ) : (
          <ScrollPanel maxHeight={320}>
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
              {filtered.map((tool) => (
                <div
                  key={tool.name}
                  style={s({
                    display: 'flex', alignItems: 'center', gap: 8, padding: '6px 8px',
                    borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay,
                  })}
                >
                  <span style={s({ ...mono, fontSize: 10, color: T.accentText, minWidth: 200, flexShrink: 0 })}>
                    {tool.name}
                  </span>
                  <span style={s({ fontSize: 10, color: T.text3, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' })}>
                    {tool.description}
                  </span>
                  <RiskChip tool={tool} />
                </div>
              ))}
            </div>
          </ScrollPanel>
        )}
      </Card>

      <Card>
        <SectionTitle>Seneste capability-kald</SectionTitle>
        {loading ? (
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
            {Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} height={28} />)}
          </div>
        ) : (data?.recent_invocations || []).length === 0 ? (
          <EmptyState title="Ingen kald endnu">Kald vil vises her efter første tool-brug.</EmptyState>
        ) : (
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 4 })}>
            {(data.recent_invocations || []).map((inv, i) => {
              const statusColor = inv.status === 'ok' ? T.green : inv.status === 'error' ? T.red : T.text3
              return (
                <div key={i} style={s({ display: 'flex', alignItems: 'center', gap: 8, padding: '5px 8px', borderRadius: 7, border: `1px solid ${T.border0}`, background: T.bgOverlay })}>
                  <span style={s({ ...mono, fontSize: 10, color: T.accentText, minWidth: 200, flexShrink: 0 })}>{inv.capability_name}</span>
                  <span style={s({ ...mono, fontSize: 9, color: statusColor, padding: '2px 7px', borderRadius: 10, background: `${statusColor}18`, border: `1px solid ${statusColor}35` })}>{inv.status}</span>
                  <span style={s({ ...mono, fontSize: 9, color: T.text3, marginLeft: 'auto' })}>{formatFreshness(inv.invoked_at)}</span>
                </div>
              )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
