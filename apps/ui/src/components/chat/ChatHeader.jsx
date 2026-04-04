import { useEffect, useMemo, useState } from 'react'
import { Activity, Search, Settings, RefreshCw } from 'lucide-react'
import { Chip } from '../shared/Chip'

function formatTokens(n) {
  if (!n && n !== 0) return '—'
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

export function ChatHeader({
  session,
  selection,
  onSelectionChange,
  onRefresh,
  isRefreshing,
  isStreaming,
  lastRunTokens,
  streamingTokenEstimate,
}) {
  const [provider, setProvider] = useState(selection.currentProvider || '')
  const [model, setModel] = useState(selection.currentModel || '')

  useEffect(() => {
    setProvider(selection.currentProvider || '')
    setModel(selection.currentModel || '')
  }, [selection.currentProvider, selection.currentModel])

  const providers = useMemo(
    () => [...new Set((selection.availableConfiguredTargets || []).map((x) => x.provider))],
    [selection.availableConfiguredTargets]
  )
  const models = useMemo(
    () => (selection.availableConfiguredTargets || []).filter((x) => x.provider === provider),
    [selection.availableConfiguredTargets, provider]
  )

  function handleProviderChange(e) {
    const next = e.target.value
    setProvider(next)
    const first = (selection.availableConfiguredTargets || []).find((x) => x.provider === next)
    if (first) {
      setModel(first.model)
      onSelectionChange?.({ provider: next, model: first.model, authProfile: first.authProfile || '' })
    }
  }

  function handleModelChange(e) {
    const next = e.target.value
    setModel(next)
    const candidate = models.find((x) => x.model === next)
    onSelectionChange?.({ provider, model: next, authProfile: candidate?.authProfile || '' })
  }

  const tokenLabel = isStreaming && streamingTokenEstimate > 0
    ? `~${formatTokens(streamingTokenEstimate)} tok`
    : lastRunTokens
      ? `${formatTokens(lastRunTokens.total)} tok`
      : '— tok'

  const tokenTitle = isStreaming
    ? `Streaming (~${streamingTokenEstimate} output tokens estimated)`
    : lastRunTokens
      ? `In: ${formatTokens(lastRunTokens.input)} / Out: ${formatTokens(lastRunTokens.output)}`
      : 'No run yet'

  return (
    <section className="chat-header-bar">
      <div className="chat-header-left">
        <span className="chat-header-session-title">{session?.title || 'Ny chat'}</span>
        <div className="chat-header-chips">
          <Chip color="#3d8f7c">L3</Chip>
          <Chip color="#d4963a">EXP</Chip>
        </div>
      </div>

      <div className="chat-header-right">
        <select
          className="header-select mono"
          value={provider}
          onChange={handleProviderChange}
          title="Provider"
        >
          {providers.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>

        <select
          className="header-select mono"
          value={model}
          onChange={handleModelChange}
          title="Model"
        >
          {models.map((m) => <option key={m.model} value={m.model}>{m.model}</option>)}
        </select>

        <div className={`chat-token-meter ${isStreaming ? 'active' : ''}`} title={tokenTitle}>
          <Activity size={9} />
          <span className="mono">{tokenLabel}</span>
        </div>

        <button className="icon-btn" onClick={onRefresh} title="Refresh">
          <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
        </button>
        <button className="icon-btn" title="Search"><Search size={14} /></button>
        <button className="icon-btn" title="Settings"><Settings size={14} /></button>
      </div>
    </section>
  )
}
