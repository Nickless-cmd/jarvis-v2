import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import { ArrowUp, Square, Paperclip, GitBranch, GitCommit, ShieldCheck, Layers, Activity, Check, X } from 'lucide-react'
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
        // Refresh git info so diff stats clear
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

      {/* Top meta row: git branch + diff + commit button + workspace */}
      {(shortBranch || shortPath) && (
        <div className="composer-meta-row">
          <div className="composer-meta-left">
            {shortBranch && (
              <div className="composer-git-info">
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
            )}
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
          {shortPath && (
            <span className="composer-workspace-path mono">{shortPath}</span>
          )}
        </div>
      )}

      {/* Inline commit field */}
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

      {/* Input row */}
      <div className={isStreaming ? 'composer-wrap working' : 'composer-wrap'}>
        <button className="icon-btn subtle composer-attach-btn" type="button" title="Attach">
          <Paperclip size={16} />
        </button>
        <textarea
          ref={textareaRef}
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

      {/* Bottom toolbar */}
      <div className="composer-toolbar">
        <div className="composer-toolbar-left">
          <div className="composer-toolbar-group" title="Tool approval mode">
            <ShieldCheck size={11} strokeWidth={1.8} className="composer-shield-icon" />
            <select
              className="composer-select mono"
              value={approvalMode}
              onChange={(e) => setApprovalMode(e.target.value)}
              title="Tool approval mode"
            >
              <option value="auto">auto</option>
              <option value="ask">ask all</option>
              <option value="trust">trust all</option>
            </select>
          </div>

          {providers.length > 0 && (
            <div className="composer-toolbar-group">
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
        </div>

        <div className="composer-toolbar-right">
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
