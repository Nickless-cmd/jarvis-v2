import { useState, useEffect } from 'react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { AnsiText } from './AnsiText'
import {
  ChevronRight,
  ChevronDown,
  FileEdit,
  Terminal,
  FileSearch,
  FolderOpen,
  Search,
  Database,
  Wrench,
  AlertCircle,
  Pin,
  PinOff,
} from 'lucide-react'

// Cross-app pin store. JarvisX has its own React hook (usePinnedResults)
// but apps/ui's MarkdownRenderer is also used standalone in webchat — so
// we expose a tiny localStorage-backed singleton here that both can read.
// Webchat doesn't (yet) render a pinned strip, but the pin button still
// works and the state syncs to JarvisX via the storage event.
const PIN_STORAGE_KEY = 'jarvisx.pinned_tool_results'
const PIN_MAX = 6

function loadPinIds() {
  try {
    const raw = localStorage.getItem(PIN_STORAGE_KEY)
    if (!raw) return new Set()
    const parsed = JSON.parse(raw)
    if (!Array.isArray(parsed)) return new Set()
    return new Set(parsed.map((p) => p?.resultId).filter(Boolean))
  } catch {
    return new Set()
  }
}

function togglePin(resultId, summary) {
  try {
    const raw = localStorage.getItem(PIN_STORAGE_KEY)
    const arr = raw ? JSON.parse(raw) : []
    const list = Array.isArray(arr) ? arr : []
    const exists = list.some((p) => p?.resultId === resultId)
    let next
    if (exists) {
      next = list.filter((p) => p?.resultId !== resultId)
    } else {
      next = [{ resultId, summary, pinnedAt: Date.now() }, ...list].slice(0, PIN_MAX)
    }
    localStorage.setItem(PIN_STORAGE_KEY, JSON.stringify(next))
    // Notify same-window listeners (storage event only fires across tabs)
    window.dispatchEvent(new CustomEvent('jarvisx:pins-changed'))
  } catch { /* ignore */ }
}

/**
 * Expandable card that replaces inline `[tool_result:tool-result-XXX]`
 * references with a tool-aware rich rendering. Lazy-fetches the full
 * payload via /api/tool-result/{id} on first expand, then renders
 * differently per tool_name:
 *
 *   edit_file / write_file  →  unified diff (red/green lines)
 *   bash / bash_session_run →  dark terminal block
 *   read_file               →  syntax-highlighted code
 *   search / grep           →  match list with file:line headers
 *   memory_*, *_search      →  prose with key:value table
 *   default                 →  pretty JSON
 *
 * The compact (collapsed) state shows just an icon + the one-line
 * summary so the chat stays readable. Click → expand. Click again →
 * collapse. State is per-card; not persisted.
 */
export function InlineToolResult({ resultId, summary }) {
  const [open, setOpen] = useState(false)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [pinned, setPinned] = useState(() => loadPinIds().has(resultId))

  useEffect(() => {
    if (!open || data || loading) return
    setLoading(true)
    fetch(`/api/tool-result/${resultId}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return r.json()
      })
      .then(setData)
      .catch((e) => setError(e.message || String(e)))
      .finally(() => setLoading(false))
  }, [open, resultId, data, loading])

  // Sync pinned status across cards / tabs
  useEffect(() => {
    const refresh = () => setPinned(loadPinIds().has(resultId))
    window.addEventListener('storage', refresh)
    window.addEventListener('jarvisx:pins-changed', refresh)
    return () => {
      window.removeEventListener('storage', refresh)
      window.removeEventListener('jarvisx:pins-changed', refresh)
    }
  }, [resultId])

  const handleTogglePin = (e) => {
    e.stopPropagation()
    togglePin(resultId, summary || '')
    setPinned((p) => !p)
  }

  // Parse summary like "[edit_file]: Edited /path (1 replacement)" → toolName + rest
  const { toolName, summaryRest } = parseSummary(summary)
  const Icon = iconForTool(toolName)

  return (
    <div className="inline-tool-result">
      <div className="inline-tool-result-header">
        <button
          className="inline-tool-result-trigger"
          onClick={() => setOpen((o) => !o)}
        >
          {open ? (
            <ChevronDown size={11} className="inline-tool-result-chev" />
          ) : (
            <ChevronRight size={11} className="inline-tool-result-chev" />
          )}
          <Icon size={11} className="inline-tool-result-icon" />
          <span className="inline-tool-result-tool">{toolName || 'tool'}</span>
          {summaryRest && (
            <span className="inline-tool-result-summary">{summaryRest}</span>
          )}
        </button>
        <button
          className={`inline-tool-result-pin ${pinned ? 'pinned' : ''}`}
          onClick={handleTogglePin}
          title={pinned ? 'Unpin' : 'Pin to top of chat'}
        >
          {pinned ? <Pin size={10} /> : <PinOff size={10} />}
        </button>
      </div>
      {open && (
        <div className="inline-tool-result-body">
          {loading && (
            <div className="inline-tool-result-loading">loading…</div>
          )}
          {error && (
            <div className="inline-tool-result-error">
              <AlertCircle size={11} /> {error}
            </div>
          )}
          {data && <ToolResultBody data={data} />}
        </div>
      )}
    </div>
  )
}

function ToolResultBody({ data }) {
  const tool = String(data.tool_name || '').toLowerCase()
  const result = data.result || data.summary || ''

  // pause_and_ask is special — render an interactive prompt with option
  // buttons rather than a generic result dump. The result payload's
  // structure is set by core/tools/pause_and_ask_tools.py.
  if (tool === 'pause_and_ask' && typeof result === 'object' && result?.kind === 'pause_and_ask') {
    return <PauseAndAskCard payload={result} />
  }

  // approval_needed — Jarvis attempted a destructive/risky tool and
  // the runtime returned approval_needed instead of executing. Show
  // an inline Approve / Deny card with the proposed action.
  if (
    typeof result === 'object' &&
    result &&
    (result.status === 'approval_needed' || result.classification === 'destructive')
  ) {
    return <ApprovalCard payload={result} toolName={tool} />
  }

  if (tool === 'edit_file' || tool === 'write_file') {
    return <DiffView text={String(result)} />
  }
  if (tool === 'bash' || tool === 'bash_session_run' || tool === 'bash_session_open') {
    return <TerminalView data={data} />
  }
  if (tool === 'read_file') {
    return <CodeView text={String(result)} path={data?.arguments?.path} />
  }
  if (tool === 'search' || tool === 'grep' || tool === 'find_files') {
    return <SearchView text={String(result)} />
  }
  // Default — pretty JSON
  return (
    <pre className="inline-tool-result-default">
      <code>{typeof result === 'string' ? result : JSON.stringify(result, null, 2)}</code>
    </pre>
  )
}

/**
 * Inline Approve / Deny / Ask card for tools that returned
 * approval_needed. Same event pattern as PauseAndAskCard — clicks
 * dispatch CustomEvents that JarvisX's ChatView turns into the next
 * user message.
 */
function ApprovalCard({ payload, toolName }) {
  const message = payload.message || `Action requires approval: ${toolName}`
  const command = payload.command || ''
  const path = payload.path || ''
  const classification = payload.classification || ''

  const respond = (verdict) => {
    const reply = verdict === 'approve'
      ? `Approved — proceed with ${toolName}.`
      : verdict === 'deny'
      ? `Denied — don't run ${toolName}. Tell me why you wanted to.`
      : `Wait — explain why you want to run ${toolName} first.`
    window.dispatchEvent(
      new CustomEvent('jarvisx:approval-response', {
        detail: { verdict, tool: toolName, reply },
      }),
    )
  }

  return (
    <div
      className="approval-card-inline"
      data-classification={classification || 'mutation'}
    >
      <div className="approval-card-message">{message}</div>
      {(command || path) && (
        <pre className="approval-card-target">
          <code>{command || path}</code>
        </pre>
      )}
      <div className="approval-card-buttons">
        <button
          onClick={() => respond('approve')}
          className="approval-btn approve"
        >
          ✓ Approve
        </button>
        <button
          onClick={() => respond('deny')}
          className="approval-btn deny"
        >
          ✗ Deny
        </button>
        <button
          onClick={() => respond('ask')}
          className="approval-btn ask"
        >
          ? Ask first
        </button>
      </div>
    </div>
  )
}

/**
 * Interactive prompt card. Buttons dispatch a window CustomEvent that
 * JarvisX's ChatView listens for and converts into a user message via
 * the shell's handleSend. In webchat (no listener), buttons fall back
 * to copying the option to clipboard for manual paste.
 */
function PauseAndAskCard({ payload }) {
  const { question, options, context: ctx, urgency } = payload
  const handlePick = (opt) => {
    const evt = new CustomEvent('jarvisx:pause-answer', {
      detail: { question, picked: opt },
    })
    window.dispatchEvent(evt)
    // Fallback for webchat — copy to clipboard if no handler
    setTimeout(() => {
      try {
        // Mark as handled if a listener responded
        if (!evt.defaultPrevented && navigator.clipboard) {
          navigator.clipboard.writeText(opt).catch(() => undefined)
        }
      } catch { /* ignore */ }
    }, 50)
  }
  const urgencyClass =
    urgency === 'high' ? 'pause-ask-urgent' : urgency === 'low' ? 'pause-ask-quiet' : ''
  return (
    <div className={`pause-ask-card ${urgencyClass}`}>
      <div className="pause-ask-question">{question}</div>
      {ctx && <div className="pause-ask-context">{ctx}</div>}
      {options && options.length > 0 ? (
        <div className="pause-ask-options">
          {options.map((opt) => (
            <button
              key={opt}
              type="button"
              onClick={() => handlePick(opt)}
              className="pause-ask-option"
            >
              {opt}
            </button>
          ))}
        </div>
      ) : (
        <div className="pause-ask-freeform">
          (free-form — type your answer in the composer)
        </div>
      )}
    </div>
  )
}

function DiffView({ text }) {
  // Detect a unified diff by looking for +/- lines. If not present, render
  // as a plain "edit summary" with no syntax markup.
  const lines = text.split('\n')
  const hasDiff = lines.some((l) => /^[+-]/.test(l) && !/^[+-]{3} /.test(l))
  if (!hasDiff) {
    return (
      <pre className="inline-tool-result-default">
        <code>{text}</code>
      </pre>
    )
  }
  return (
    <div className="inline-tool-result-diff">
      {lines.map((line, i) => {
        let cls = 'diff-context'
        if (line.startsWith('+++ ') || line.startsWith('--- ')) cls = 'diff-meta'
        else if (line.startsWith('+')) cls = 'diff-add'
        else if (line.startsWith('-')) cls = 'diff-del'
        else if (line.startsWith('@@')) cls = 'diff-hunk'
        return (
          <div key={i} className={`diff-line ${cls}`}>
            <span className="diff-gutter">{line[0] || ' '}</span>
            <span className="diff-text">{line.slice(line[0] ? 1 : 0)}</span>
          </div>
        )
      })}
    </div>
  )
}

function TerminalView({ data }) {
  const args = data.arguments || {}
  const cmd = args.command || ''
  let output = ''
  let exitCode = null
  // bash_session_run returns an object {session_id, command, exit_code, output}
  // bash returns {text, exit_code, status} or {error,...}
  if (typeof data.result === 'object' && data.result !== null) {
    output = data.result.output ?? data.result.text ?? data.result.stdout ?? ''
    exitCode = data.result.exit_code
    if (data.result.error) output = (output ? output + '\n' : '') + '[stderr] ' + data.result.error
  } else if (typeof data.result === 'string') {
    // Some bash results are raw strings. Try to parse JSON-shaped output.
    try {
      const parsed = JSON.parse(data.result)
      if (parsed && typeof parsed === 'object') {
        output = parsed.output ?? parsed.text ?? parsed.stdout ?? data.result
        exitCode = parsed.exit_code
      } else {
        output = data.result
      }
    } catch {
      output = data.result
    }
  }
  return (
    <div className="inline-tool-result-terminal">
      {cmd && (
        <div className="terminal-prompt">
          <span className="terminal-prompt-sigil">$</span>
          <span className="terminal-prompt-cmd">{cmd}</span>
        </div>
      )}
      <pre className="terminal-output">
        <code>
          {output ? <AnsiText text={output} /> : '(no output)'}
        </code>
      </pre>
      {exitCode != null && (
        <div className={`terminal-exit ${exitCode === 0 ? 'ok' : 'fail'}`}>
          exit {exitCode}
        </div>
      )}
    </div>
  )
}

function CodeView({ text, path }) {
  const lang = languageFromPath(path)
  return (
    <div className="inline-tool-result-code">
      {path && <div className="code-path">{path}</div>}
      <SyntaxHighlighter
        language={lang}
        style={oneDark}
        customStyle={{
          margin: 0,
          borderRadius: 4,
          fontSize: '0.82em',
          background: '#0d1117',
          maxHeight: '400px',
          overflow: 'auto',
        }}
      >
        {text}
      </SyntaxHighlighter>
    </div>
  )
}

function SearchView({ text }) {
  // Heuristic: lines like "path:line:content" → render as a list
  const lines = text.split('\n').filter((l) => l.trim())
  return (
    <div className="inline-tool-result-search">
      {lines.map((line, i) => {
        const m = line.match(/^([^:]+):(\d+):(.+)$/)
        if (m) {
          return (
            <div key={i} className="search-hit">
              <span className="search-hit-path">{m[1]}</span>
              <span className="search-hit-lineno">:{m[2]}</span>
              <span className="search-hit-text">{m[3]}</span>
            </div>
          )
        }
        return (
          <div key={i} className="search-line">
            {line}
          </div>
        )
      })}
    </div>
  )
}

// ── Helpers ───────────────────────────────────────────────────────

function parseSummary(summary) {
  if (!summary) return { toolName: '', summaryRest: '' }
  // Match "[tool_name]: rest of summary"
  const m = summary.match(/^\[([\w_]+)\]:\s*(.*)$/)
  if (m) return { toolName: m[1], summaryRest: m[2] }
  return { toolName: '', summaryRest: summary }
}

function iconForTool(toolName) {
  const name = String(toolName || '').toLowerCase()
  if (name.includes('edit') || name.includes('write') || name.includes('patch'))
    return FileEdit
  if (name === 'bash' || name.startsWith('bash_session')) return Terminal
  if (name.includes('read')) return FileSearch
  if (name.includes('search') || name.includes('grep')) return Search
  if (name.includes('find') || name.includes('list')) return FolderOpen
  if (name.includes('memory') || name.includes('db')) return Database
  return Wrench
}

const EXT_LANG = {
  py: 'python',
  js: 'javascript',
  jsx: 'jsx',
  ts: 'typescript',
  tsx: 'tsx',
  md: 'markdown',
  json: 'json',
  sh: 'bash',
  yml: 'yaml',
  yaml: 'yaml',
  toml: 'toml',
  html: 'html',
  css: 'css',
  sql: 'sql',
  go: 'go',
  rs: 'rust',
}

function languageFromPath(path) {
  if (!path) return 'text'
  const m = String(path).match(/\.([a-zA-Z0-9]+)$/)
  if (!m) return 'text'
  return EXT_LANG[m[1].toLowerCase()] || 'text'
}
