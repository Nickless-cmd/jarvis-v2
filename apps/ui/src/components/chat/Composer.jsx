import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ArrowUp, Square, Plus, GitBranch, GitCommit, ShieldCheck, Layers, Activity, Check, X, Monitor } from 'lucide-react'
import { backend } from '../../lib/adapters'

function formatTokens(n) {
  if (!n && n !== 0) return null
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}

function formatDiff(ins, dels) {
  const parts = []
  if (ins > 0) parts.push(`+${ins > 999 ? Math.round(ins / 100) / 10 + 'k' : ins}`)
  if (dels > 0) parts.push(`-${dels > 999 ? Math.round(dels / 100) / 10 + 'k' : dels}`)
  return parts
}

export function Composer({
  value,
  onChange,
  onSend,
  onCancel,
  isStreaming,
  selection,
  onSelectionChange,
  lastRunTokens,
  streamingTokenEstimate,
}) {
  const textareaRef = useRef(null)
  const commitInputRef = useRef(null)
  const canSend = Boolean(value.trim()) && !isStreaming

  const [planMode, setPlanMode] = useState(false)
  const [approvalMode, setApprovalMode] = useState('auto')
  const [gitInfo, setGitInfo] = useState(null)
  const [commitOpen, setCommitOpen] = useState(false)
  const [commitMsg, setCommitMsg] = useState('')
  const [commitState, setCommitState] = useState('idle') // idle | loading | error
  const [commitError, setCommitError] = useState('')
  const [provider, setProvider] = useState(selection?.currentProvider || '')
  const [model, setModel] = useState(selection?.currentModel || '')

  useEffect(() => {
    setProvider(selection?.currentProvider || '')
    setModel(selection?.currentModel || '')
  }, [selection?.currentProvider, selection?.currentModel])

  // Fetch git info on mount and every 30s
  useEffect(() => {
    async function fetchGit() {
      const info = await backend.getSystemGit()
      setGitInfo(info)
    }
    fetchGit()
    const id = setInterval(fetchGit, 30_000)
    return () => clearInterval(id)
  }, [])

  // Focus commit input when opened
  useEffect(() => {
    if (commitOpen) commitInputRef.current?.focus()
  }, [commitOpen])

  useLayoutEffect(() => {
    const node = textareaRef.current
    if (!node) return
    node.style.height = '0px'
    node.style.height = `${Math.min(node.scrollHeight, 160)}px`
  }, [value])

  const configuredTargets = selection?.availableConfiguredTargets || []
  const providers = useMemo(
    () => [...new Set([selection?.currentProvider || '', ...configuredTargets.map((x) => x.provider)].filter(Boolean))],
    [configuredTargets, selection?.currentProvider]
  )
  const models = useMemo(() => {
    // For ollama: use the full live model list (includes cloud models) instead of only configured targets
    if (provider === 'ollama') {
      const ollamaModels = (selection?.ollamaModels || [])
        .filter((m) => m.name && !m.family?.includes('bert') && !m.name.includes('embed'))
        .map((m) => ({ model: m.name, label: m.name }))
      if (ollamaModels.length) return ollamaModels
    }
    const forProvider = configuredTargets.filter((x) => x.provider === provider)
    return forProvider.length
      ? forProvider.map((x) => ({ model: x.model, label: x.model }))
      : provider === selection?.currentProvider && selection?.currentModel
        ? [{ model: selection.currentModel, label: selection.currentModel }]
        : []
  }, [configuredTargets, provider, selection])

  function handleProviderChange(e) {
    const next = e.target.value
    setProvider(next)
    const first = configuredTargets.find((x) => x.provider === next)
    const nextModel = first?.model || ''
    setModel(nextModel)
    if (nextModel) onSelectionChange?.({ provider: next, model: nextModel, authProfile: first?.authProfile || '' })
  }

  function handleModelChange(e) {
    const next = e.target.value
    setModel(next)
    const candidate = configuredTargets.find((x) => x.model === next)
    onSelectionChange?.({ provider, model: next, authProfile: candidate?.authProfile || '' })
  }

  function handleSend() {
    if (!canSend) return
    const msg = planMode ? `[Plan mode] ${value.trim()}` : value.trim()
    onSend(msg, { approvalMode })
  }

  function openCommit() {
    setCommitMsg('')
    setCommitError('')
    setCommitState('idle')
    setCommitOpen(true)
  }

  function cancelCommit() {
    setCommitOpen(false)
    setCommitMsg('')
    setCommitError('')
    setCommitState('idle')
  }

  async function submitCommit() {
    const msg = commitMsg.trim()
    if (!msg) return
    setCommitState('loading')
    setCommitError('')
    try {
      const result = await backend.gitCommit(msg)
      if (result.ok) {
        setCommitOpen(false)
        setCommitMsg('')
        setCommitState('idle')
        const info = await backend.getSystemGit()
        setGitInfo(info)
      } else {
        setCommitState('error')
        setCommitError(result.error || 'Commit failed')
      }
    } catch (err) {
      setCommitState('error')
      setCommitError(String(err))
    }
  }

  const tokenLabel = isStreaming && streamingTokenEstimate > 0
    ? formatTokens(streamingTokenEstimate)
    : formatTokens(lastRunTokens?.total)

  const diffParts = gitInfo ? formatDiff(gitInfo.insertions, gitInfo.deletions) : []
  const shortBranch = gitInfo?.branch || ''
  const shortPath = gitInfo?.workspace
    ? gitInfo.workspace.replace(/^\/media\/projects\//, '~/')
    : ''
  const hasChanges = (gitInfo?.files_changed || 0) > 0

  return (
    <section className="composer-shell">

      {/* Inline commit field (shown above the card) */}
      {commitOpen && (
        <div className="composer-commit-row">
          <GitCommit size={12} strokeWidth={1.8} className="composer-commit-icon" />
          <input
            ref={commitInputRef}
            className="composer-commit-input mono"
            type="text"
            value={commitMsg}
            onChange={(e) => setCommitMsg(e.target.value)}
            placeholder="Commit message…"
            disabled={commitState === 'loading'}
            onKeyDown={(e) => {
              if (e.key === 'Enter') submitCommit()
              if (e.key === 'Escape') cancelCommit()
            }}
          />
          {commitError && (
            <span className="composer-commit-error mono">{commitError}</span>
          )}
          <button
            className="composer-commit-confirm"
            onClick={submitCommit}
            disabled={!commitMsg.trim() || commitState === 'loading'}
            title="Confirm commit"
            type="button"
          >
            <Check size={12} />
          </button>
          <button
            className="composer-commit-cancel"
            onClick={cancelCommit}
            title="Cancel"
            type="button"
          >
            <X size={12} />
          </button>
        </div>
      )}

      {/* Main card */}
      <div className={`composer-card${isStreaming ? ' working' : ''}`}>

        {/* Git bar */}
        {shortBranch && (
          <div className="composer-git-bar">
            <div className="composer-git-bar-left">
              <GitBranch size={11} strokeWidth={1.8} />
              <span className="mono">{shortBranch}</span>
              {diffParts.length > 0 && (
                <span className="composer-diff-stats mono">
                  {diffParts.map((part, i) => (
                    <span key={i} className={part.startsWith('+') ? 'diff-ins' : 'diff-dels'}>{part}</span>
                  ))}
                </span>
              )}
            </div>
            <div className="composer-git-bar-right">
              {hasChanges && !commitOpen && (
                <button
                  className="composer-commit-btn"
                  onClick={openCommit}
                  title="Commit changes"
                  type="button"
                >
                  <GitCommit size={11} strokeWidth={1.8} />
                  <span>Commit changes</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSend()
            }
          }}
          placeholder={
            isStreaming
              ? 'Jarvis is responding…'
              : planMode
                ? 'Describe what to plan…'
                : 'Message Jarvis…'
          }
          rows={1}
        />

        {/* Toolbar row */}
        <div className="composer-toolbar">
          <div className="composer-toolbar-left">
            <button className="composer-attach-btn icon-btn subtle" type="button" title="Attach">
              <Plus size={14} />
            </button>
            <div className="composer-permissions-group" title="Tool approval mode">
              <ShieldCheck size={11} strokeWidth={1.8} className="composer-shield-icon" />
              <select
                className="composer-select mono"
                value={approvalMode}
                onChange={(e) => setApprovalMode(e.target.value)}
              >
                <option value="auto">Auto</option>
                <option value="ask">Ask permissions</option>
                <option value="trust">Trust all</option>
              </select>
            </div>
          </div>

          <div className="composer-toolbar-right">
            {providers.length > 0 && (
              <div className="composer-model-group">
                <select
                  className="composer-select mono"
                  value={provider}
                  onChange={handleProviderChange}
                  title="Provider"
                >
                  {providers.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
                {models.length > 0 && (
                  <>
                    <span className="composer-select-sep mono">/</span>
                    <select
                      className="composer-select mono"
                      value={model}
                      onChange={handleModelChange}
                      title="Model"
                    >
                      {models.map((m) => <option key={m.model} value={m.model}>{m.label}</option>)}
                    </select>
                  </>
                )}
              </div>
            )}

            {isStreaming ? (
              <button className="send-btn cancel" onClick={onCancel} title="Stop generating">
                <Square size={14} />
              </button>
            ) : (
              <button
                className="send-btn"
                onClick={handleSend}
                disabled={!canSend}
                title={canSend ? 'Send message' : 'Write a message first'}
              >
                <ArrowUp size={16} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Footer row */}
      <div className="composer-footer">
        <div className="composer-footer-left">
          {shortPath && (
            <>
              <Monitor size={10} strokeWidth={1.6} />
              <span className="composer-workspace-path mono">{shortPath}</span>
            </>
          )}
        </div>
        <div className="composer-footer-right">
          <button
            className={`composer-plan-btn${planMode ? ' active' : ''}`}
            onClick={() => setPlanMode(!planMode)}
            title={planMode ? 'Plan mode on — click to disable' : 'Enable plan mode'}
            type="button"
          >
            <Layers size={11} strokeWidth={1.8} />
            <span>Plan</span>
          </button>

          {tokenLabel && (
            <div
              className="composer-token-count mono"
              title={lastRunTokens ? `In: ${lastRunTokens.input} / Out: ${lastRunTokens.output}` : ''}
            >
              <Activity size={9} />
              <span>{tokenLabel}</span>
            </div>
          )}
        </div>
      </div>

    </section>
  )
}
