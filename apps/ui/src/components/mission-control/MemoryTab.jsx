import { useEffect, useMemo, useState } from 'react'
import { Search, RefreshCcw } from 'lucide-react'
import { backend } from '../../lib/adapters'
import { s, T, mono } from '../../shared/theme/tokens'
import { Card, SectionTitle, EmptyState, Skeleton, ScrollPanel, MetricCard } from './shared'
import { formatFreshness } from './meta'

function ScopePill({ scope, active, onClick }) {
  const color = active ? T.accent : T.text3
  return (
    <button
      onClick={onClick}
      style={s({
        ...mono, fontSize: 9, padding: '3px 8px', borderRadius: 10,
        background: active ? `${T.accent}22` : T.bgOverlay,
        border: `1px solid ${active ? T.accent : T.border1}`,
        color, cursor: 'pointer',
      })}
    >
      {scope.label} <span style={s({ color: T.text3 })}>· {scope.count}</span>
    </button>
  )
}

export function MemoryTab() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [query, setQuery] = useState('')
  const [scopeFilter, setScopeFilter] = useState('')
  const [debouncedQuery, setDebouncedQuery] = useState('')
  const [fetchedAt, setFetchedAt] = useState('')

  // Debounce search input — avoid hammering the endpoint per keystroke.
  useEffect(() => {
    const handle = window.setTimeout(() => setDebouncedQuery(query), 250)
    return () => window.clearTimeout(handle)
  }, [query])

  useEffect(() => {
    let cancelled = false
    async function load() {
      setLoading(true)
      try {
        const result = await backend.getMissionControlMemory({
          query: debouncedQuery,
          scope: scopeFilter,
          limit: 100,
        })
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
  }, [debouncedQuery, scopeFilter])

  const items = data?.items || []
  const total = data?.total || 0
  const matched = data?.matched || 0
  const scopeCounts = data?.scope_counts || {}
  const scopes = useMemo(
    () => Object.entries(scopeCounts).map(([label, count]) => ({ label, count })),
    [scopeCounts]
  )

  return (
    <div style={s({ display: 'flex', flexDirection: 'column', gap: 16 })}>
      <div style={s({ display: 'flex', alignItems: 'center', gap: 10 })}>
        <span style={s({ fontSize: 14, fontWeight: 500, color: T.text1 })}>Memory</span>
        <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
          {fetchedAt ? formatFreshness(fetchedAt) : ''}
        </span>
        <button
          onClick={() => setDebouncedQuery((v) => v + '')}
          disabled={loading}
          style={s({
            marginLeft: 'auto', padding: '4px 8px', borderRadius: 7,
            border: `1px solid ${T.border1}`, background: T.bgOverlay,
            color: T.text2, cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.5 : 1,
          })}
          title="Refresh"
        >
          <RefreshCcw size={11} />
        </button>
      </div>

      <div style={s({ display: 'flex', gap: 10 })}>
        <MetricCard label="Records i alt" value={loading ? '…' : total} />
        <MetricCard label="Viser" value={loading ? '…' : matched} />
        <MetricCard label="Scopes" value={loading ? '…' : scopes.length} />
      </div>

      <div style={s({ display: 'flex', alignItems: 'center', gap: 8 })}>
        <div style={s({
          display: 'flex', alignItems: 'center', gap: 6, flex: 1,
          padding: '6px 10px', background: T.bgOverlay,
          border: `1px solid ${T.border1}`, borderRadius: 6,
        })}>
          <Search size={11} color={T.text3} />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Søg i hukommelsen…"
            style={s({
              flex: 1, background: 'transparent', border: 'none',
              color: T.text1, fontSize: 11, ...mono, outline: 'none',
            })}
          />
        </div>
      </div>

      {scopes.length > 0 ? (
        <div style={s({ display: 'flex', gap: 6, flexWrap: 'wrap' })}>
          <ScopePill
            scope={{ label: 'alle', count: total }}
            active={!scopeFilter}
            onClick={() => setScopeFilter('')}
          />
          {scopes.map((sc) => (
            <ScopePill
              key={sc.label}
              scope={sc}
              active={scopeFilter === sc.label}
              onClick={() => setScopeFilter(scopeFilter === sc.label ? '' : sc.label)}
            />
          ))}
        </div>
      ) : null}

      <Card>
        <SectionTitle>Memory items</SectionTitle>
        {loading ? (
          <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} height={48} />)}
          </div>
        ) : items.length === 0 ? (
          <EmptyState title="Ingen records matcher">
            {debouncedQuery ? 'Prøv et andet søgeord eller scope.' : 'Endnu ingen retained memory.'}
          </EmptyState>
        ) : (
          <ScrollPanel maxHeight={520}>
            <div style={s({ display: 'flex', flexDirection: 'column', gap: 6 })}>
              {items.map((item) => (
                <div
                  key={item.id}
                  style={s({
                    display: 'flex', flexDirection: 'column', gap: 4,
                    padding: '8px 10px', borderRadius: 7,
                    border: `1px solid ${T.border0}`, background: T.bgOverlay,
                  })}
                >
                  <div style={s({ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' })}>
                    <span style={s({
                      ...mono, fontSize: 9, padding: '2px 7px', borderRadius: 10,
                      background: `${T.accent}18`, border: `1px solid ${T.accent}35`,
                      color: T.accentText,
                    })}>
                      {item.kind || 'record'}
                    </span>
                    <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
                      scope: {item.scope || '—'}
                    </span>
                    <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
                      horizon: {item.horizon || '—'}
                    </span>
                    <span style={s({ ...mono, fontSize: 9, color: T.text3 })}>
                      confidence: {item.confidence || '—'}
                    </span>
                    <span style={s({ ...mono, fontSize: 9, color: T.text3, marginLeft: 'auto' })}>
                      {formatFreshness(item.created_at)}
                    </span>
                  </div>
                  <span style={s({
                    fontSize: 11, color: T.text1, lineHeight: 1.4,
                    whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                  })}>
                    {item.value}
                  </span>
                </div>
              ))}
            </div>
          </ScrollPanel>
        )}
      </Card>
    </div>
  )
}
