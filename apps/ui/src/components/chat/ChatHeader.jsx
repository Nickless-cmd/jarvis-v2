import { useEffect, useMemo, useRef, useState } from 'react'
import { Activity, MoreVertical, Search, RefreshCw, X } from 'lucide-react'
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
  onRename,
  onDelete,
  isRefreshing,
  isStreaming,
  lastRunTokens,
  streamingTokenEstimate,
  messages,
}) {
  const [provider, setProvider] = useState(selection.currentProvider || '')
  const [model, setModel] = useState(selection.currentModel || '')
  const [menuOpen, setMenuOpen] = useState(false)
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const menuRef = useRef(null)
  const searchInputRef = useRef(null)

  useEffect(() => {
    setProvider(selection.currentProvider || '')
    setModel(selection.currentModel || '')
  }, [selection.currentProvider, selection.currentModel])

  // Close menu on click outside
  useEffect(() => {
    if (!menuOpen) return
    function handleClick(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false)
    }
    function handleEsc(e) { if (e.key === 'Escape') setMenuOpen(false) }
    document.addEventListener('mousedown', handleClick)
    document.addEventListener('keydown', handleEsc)
    return () => {
      document.removeEventListener('mousedown', handleClick)
      document.removeEventListener('keydown', handleEsc)
    }
  }, [menuOpen])

  // Focus search input when opened
  useEffect(() => {
    if (searchOpen) searchInputRef.current?.focus()
  }, [searchOpen])

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

  function handleRename() {
    setMenuOpen(false)
    const newTitle = prompt('Rename session:', session?.title || '')
    if (newTitle?.trim()) onRename?.(newTitle.trim())
  }

  function handleDelete() {
    setMenuOpen(false)
    if (confirm('Delete this session? This cannot be undone.')) {
      onDelete?.()
    }
  }

  // Search: filter messages
  const searchResults = useMemo(() => {
    if (!searchOpen || !searchQuery.trim()) return []
    const q = searchQuery.toLowerCase()
    return (messages || []).filter(m =>
      (m.content || '').toLowerCase().includes(q)
    ).slice(0, 20)
  }, [searchOpen, searchQuery, messages])

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
    <>
      <section className="chat-header-bar">
        <div className="chat-header-left">
          <span className="chat-header-session-title">{session?.title || 'Ny chat'}</span>
          <div className="chat-header-chips">
            <Chip color="#3d8f7c">L3</Chip>
            <Chip color="#d4963a">EXP</Chip>
          </div>
        </div>

        <div className="chat-header-right">
          <select className="header-select mono" value={provider} onChange={handleProviderChange} title="Provider">
            {providers.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>

          <select className="header-select mono" value={model} onChange={handleModelChange} title="Model">
            {models.map((m) => <option key={m.model} value={m.model}>{m.model}</option>)}
          </select>

          <div className={`chat-token-meter ${isStreaming ? 'active' : ''}`} title={tokenTitle}>
            <Activity size={9} />
            <span className="mono">{tokenLabel}</span>
          </div>

          <button className="icon-btn" onClick={onRefresh} title="Refresh">
            <RefreshCw size={14} className={isRefreshing ? 'spin' : ''} />
          </button>
          <button className="icon-btn" title="Search" onClick={() => { setSearchOpen(!searchOpen); setSearchQuery('') }}>
            <Search size={14} />
          </button>

          <div className="header-menu-anchor" ref={menuRef}>
            <button className="icon-btn" title="Session options" onClick={() => setMenuOpen(!menuOpen)}>
              <MoreVertical size={14} />
            </button>
            {menuOpen && (
              <div className="header-dropdown-menu">
                <button className="header-dropdown-item" onClick={handleRename}>Rename</button>
                <button className="header-dropdown-item danger" onClick={handleDelete}>Delete</button>
              </div>
            )}
          </div>
        </div>
      </section>

      {searchOpen && (
        <div className="chat-search-bar">
          <Search size={13} className="chat-search-icon" />
          <input
            ref={searchInputRef}
            className="chat-search-input mono"
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search in chat..."
            onKeyDown={(e) => { if (e.key === 'Escape') { setSearchOpen(false); setSearchQuery('') } }}
          />
          <button className="icon-btn" onClick={() => { setSearchOpen(false); setSearchQuery('') }}>
            <X size={13} />
          </button>
          {searchQuery.trim() && (
            <div className="chat-search-results">
              {searchResults.length === 0 ? (
                <div className="chat-search-empty mono">No matches</div>
              ) : (
                searchResults.map((m, i) => (
                  <div key={m.id || i} className="chat-search-result">
                    <span className="chat-search-result-role mono">{m.role === 'assistant' ? 'Jarvis' : 'You'}</span>
                    <span className="chat-search-result-text">{(m.content || '').slice(0, 120)}</span>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </>
  )
}
