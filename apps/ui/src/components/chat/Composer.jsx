import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'

// Smiley → emoji conversion (triggers when space/newline follows the smiley)
const SMILEY_REPLACEMENTS = [
  [/:\-\)/g, '😊'], [/:\)/g, '😊'],
  [/:\-D/g, '😄'], [/:D/g, '😄'],
  [/;\-\)/g, '😉'], [/;\)/g, '😉'],
  [/:\-P/gi, '😛'], [/:P/gi, '😛'],
  [/:\-\(/g, '😢'], [/:\(/g, '😢'],
  [/:\-O/gi, '😮'], [/:O/gi, '😮'],
  [/:\-\|/g, '😐'], [/:\|/g, '😐'],
  [/>:\(/g, '😠'],
  [/:\*/g, '😘'],
  [/<3/g, '❤️'],
  [/<\/3/g, '💔'],
  [/XD/g, '😆'],
  [/xD/g, '😆'],
]

function applySmileys(text) {
  // Only replace smileys that are followed by whitespace or end-of-string
  // to avoid mangling mid-word text
  let result = text
  for (const [pattern, emoji] of SMILEY_REPLACEMENTS) {
    result = result.replace(
      new RegExp(pattern.source + '(?=\\s|$)', pattern.flags),
      emoji,
    )
  }
  return result
}
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

function fileIcon(mime) {
  if (mime.startsWith('image/')) return '🖼️'
  if (mime.includes('zip')) return '📦'
  if (mime.includes('tar') || mime.includes('gzip')) return '🗜️'
  if (mime.includes('rar')) return '🗜️'
  return '📎'
}

function formatBytes(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
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
  sessionId,
}) {
  const textareaRef = useRef(null)
  const commitInputRef = useRef(null)
  const fileInputRef = useRef(null)

  const [planMode, setPlanMode] = useState(false)
  const [approvalMode, setApprovalMode] = useState('auto')
  const [gitInfo, setGitInfo] = useState(null)
  const [commitOpen, setCommitOpen] = useState(false)
  const [commitMsg, setCommitMsg] = useState('')
  const [commitState, setCommitState] = useState('idle')
  const [commitError, setCommitError] = useState('')
  const [provider, setProvider] = useState(selection?.currentProvider || '')
  const [model, setModel] = useState(selection?.currentModel || '')
  const [attachments, setAttachments] = useState([])
  // attachments: [{localId, filename, mime, size, status, objectUrl, serverId}]
  // status: 'uploading' | 'done' | 'error'
  const [isDragOver, setIsDragOver] = useState(false)

  const doneAttachments = attachments.filter((a) => a.status === 'done')
  const canSend = (Boolean(value.trim()) || doneAttachments.length > 0) && !isStreaming

  useEffect(() => {
    setProvider(selection?.currentProvider || '')
    setModel(selection?.currentModel || '')
  }, [selection?.currentProvider, selection?.currentModel])

  useEffect(() => {
    async function fetchGit() {
      const info = await backend.getSystemGit()
      setGitInfo(info)
    }
    fetchGit()
    const id = setInterval(fetchGit, 30_000)
    return () => clearInterval(id)
  }, [])

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

  async function addFiles(files) {
    if (!sessionId) return
    const newItems = Array.from(files).map((file) => ({
      localId: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
      filename: file.name,
      mime: file.type || 'application/octet-stream',
      size: file.size,
      status: 'uploading',
      objectUrl: file.type?.startsWith('image/') ? URL.createObjectURL(file) : null,
      serverId: null,
      _file: file,
    }))
    setAttachments((prev) => [...prev, ...newItems])

    for (const item of newItems) {
      try {
        const result = await backend.uploadAttachment(sessionId, item._file)
        setAttachments((prev) =>
          prev.map((a) => a.localId === item.localId ? { ...a, status: 'done', serverId: result.id } : a)
        )
      } catch {
        setAttachments((prev) =>
          prev.map((a) => a.localId === item.localId ? { ...a, status: 'error' } : a)
        )
      }
    }
  }

  function removeAttachment(localId) {
    setAttachments((prev) => {
      const item = prev.find((a) => a.localId === localId)
      if (item?.objectUrl) URL.revokeObjectURL(item.objectUrl)
      return prev.filter((a) => a.localId !== localId)
    })
  }

  function handleSend() {
    if (!canSend) return
    const msg = planMode ? `[Plan mode] ${value.trim()}` : value.trim()
    const attachmentIds = doneAttachments.map((a) => a.serverId)
    const attachmentMeta = doneAttachments.map((a) => ({
      id: a.serverId,
      filename: a.filename,
      mimeType: a.mime,
      objectUrl: a.objectUrl,
    }))
    onSend(msg, { approvalMode, attachmentIds, attachmentMeta })
    setAttachments([])
  }

  function handleDragOver(e) {
    e.preventDefault()
    setIsDragOver(true)
  }

  function handleDragLeave(e) {
    if (!e.currentTarget.contains(e.relatedTarget)) setIsDragOver(false)
  }

  function handleDrop(e) {
    e.preventDefault()
    setIsDragOver(false)
    if (e.dataTransfer.files.length) addFiles(e.dataTransfer.files)
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
  const uploadingCount = attachments.filter((a) => a.status === 'uploading').length

  return (
    <section className="composer-shell">
      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept="image/*,.zip,.tar,.tar.gz,.tgz,.tar.bz2,.rar"
        style={{ display: 'none' }}
        onChange={(e) => { if (e.target.files?.length) addFiles(e.target.files); e.target.value = '' }}
      />

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
          <button className="composer-commit-confirm" onClick={submitCommit}
            disabled={!commitMsg.trim() || commitState === 'loading'} title="Confirm commit" type="button">
            <Check size={12} />
          </button>
          <button className="composer-commit-cancel" onClick={cancelCommit} title="Cancel" type="button">
            <X size={12} />
          </button>
        </div>
      )}

      <div
        className={`composer-card${isStreaming ? ' working' : ''}${isDragOver ? ' drop-active' : ''}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
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
                <button className="composer-commit-btn" onClick={openCommit} title="Commit changes" type="button">
                  <GitCommit size={11} strokeWidth={1.8} />
                  <span>Commit changes</span>
                </button>
              )}
            </div>
          </div>
        )}

        {/* Attachment tray */}
        {attachments.length > 0 && (
          <div className="composer-attachment-tray">
            {attachments.map((item) =>
              item.objectUrl ? (
                <div key={item.localId} className={`attachment-thumb${item.status === 'error' ? ' error-state' : ''}`}>
                  <img src={item.objectUrl} alt={item.filename} />
                  <span className="attachment-thumb-label">{item.filename}</span>
                  {item.status === 'uploading' && (
                    <div className="attachment-thumb-progress" style={{ width: '60%' }} />
                  )}
                  <button className="attachment-thumb-remove" onClick={() => removeAttachment(item.localId)}>×</button>
                </div>
              ) : (
                <div key={item.localId} className="attachment-file-card">
                  <span className="attachment-file-card-icon">{fileIcon(item.mime)}</span>
                  <span className="attachment-file-card-name">{item.filename}</span>
                  <span className="attachment-file-card-size">{formatBytes(item.size)}</span>
                  <button className="attachment-thumb-remove" onClick={() => removeAttachment(item.localId)}>×</button>
                </div>
              )
            )}
          </div>
        )}

        <textarea
          ref={textareaRef}
          className="composer-textarea"
          value={value}
          onChange={(e) => {
            const raw = e.target.value
            // Convert smileys that are now followed by whitespace
            const converted = applySmileys(raw)
            onChange(converted)
          }}
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

        <div className="composer-toolbar">
          <div className="composer-toolbar-left">
            <button
              className="composer-attach-btn icon-btn subtle"
              type="button"
              title="Attach file or image"
              onClick={() => fileInputRef.current?.click()}
            >
              <Plus size={14} />
            </button>
            <div className="composer-permissions-group" title="Tool approval mode">
              <ShieldCheck size={11} strokeWidth={1.8} className="composer-shield-icon" />
              <select className="composer-select mono" value={approvalMode} onChange={(e) => setApprovalMode(e.target.value)}>
                <option value="auto">Auto</option>
                <option value="ask">Ask permissions</option>
                <option value="trust">Trust all</option>
              </select>
            </div>
          </div>

          <div className="composer-toolbar-right">
            {providers.length > 0 && (
              <div className="composer-model-group">
                <select className="composer-select mono" value={provider} onChange={handleProviderChange} title="Provider">
                  {providers.map((p) => <option key={p} value={p}>{p}</option>)}
                </select>
                {models.length > 0 && (
                  <>
                    <span className="composer-select-sep mono">/</span>
                    <select className="composer-select mono" value={model} onChange={handleModelChange} title="Model">
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
              <button className="send-btn" onClick={handleSend} disabled={!canSend}
                title={canSend ? 'Send message' : 'Write a message or attach a file first'}>
                <ArrowUp size={16} />
              </button>
            )}
          </div>
        </div>
      </div>

      {attachments.length > 0 && (
        <div className="attachment-status-line">
          {attachments.length} vedhæftet{attachments.length !== 1 ? 'e' : ''}
          {uploadingCount > 0 ? ` · ${uploadingCount} uploades stadig` : ''}
        </div>
      )}

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
            <div className="composer-token-count mono"
              title={lastRunTokens ? `In: ${lastRunTokens.input} / Out: ${lastRunTokens.output}` : ''}>
              <Activity size={9} />
              <span>{tokenLabel}</span>
            </div>
          )}
        </div>
      </div>
    </section>
  )
}
