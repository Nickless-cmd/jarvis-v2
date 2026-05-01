import { useCallback, useEffect, useState } from 'react'
import { FileText, X, Copy, Check, Loader2, AlertCircle } from 'lucide-react'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism'

interface Props {
  apiBaseUrl: string
  projectRoot: string
  open: boolean
  onClose: () => void
  /**
   * Path to preview. When this changes, the pane fetches the file
   * content. Empty string clears the pane to its empty state.
   */
  previewPath: string
}

const MAX_BYTES = 256 * 1024
const EXT_LANG: Record<string, string> = {
  ts: 'typescript', tsx: 'tsx',
  js: 'javascript', jsx: 'jsx',
  py: 'python',
  rs: 'rust',
  go: 'go',
  rb: 'ruby',
  java: 'java',
  kt: 'kotlin',
  swift: 'swift',
  c: 'c', h: 'c',
  cpp: 'cpp', hpp: 'cpp', cc: 'cpp',
  cs: 'csharp',
  sh: 'bash', bash: 'bash', zsh: 'bash',
  sql: 'sql',
  yml: 'yaml', yaml: 'yaml',
  json: 'json',
  toml: 'toml',
  md: 'markdown', markdown: 'markdown',
  html: 'html', xml: 'xml', svg: 'xml',
  css: 'css', scss: 'scss',
  graphql: 'graphql', gql: 'graphql',
  dockerfile: 'docker',
}

function langFor(path: string): string {
  const m = /\.([^.]+)$/.exec(path)
  if (m) {
    const lang = EXT_LANG[m[1].toLowerCase()]
    if (lang) return lang
  }
  if (/(^|\/)Dockerfile$/i.test(path)) return 'docker'
  if (/(^|\/)Makefile$/i.test(path)) return 'makefile'
  return 'text'
}

/**
 * Right-side file preview pane. Listens to `jarvisx:preview-file`
 * custom events from anywhere in the app — file tree clicks, tool
 * result file links, @file mentions in chat, future inline file
 * pills — and shows the file content with syntax highlighting.
 *
 * v1 limitations:
 *   - Read-only. Edit goes through the Composer + Jarvis tools.
 *   - Single file at a time (no tabs yet — when usage shows it
 *     matters, add a tab strip header)
 *   - 256 KB hard cap. Larger files render the head with a notice.
 *   - No jump-to-line. detail.lineNumber is accepted in the event
 *     payload for forward-compat but not yet used.
 *
 * Stays in sync with the chat by being event-driven: any component
 * that knows about a file can dispatch
 *
 *   window.dispatchEvent(new CustomEvent('jarvisx:preview-file', {
 *     detail: { path: 'apps/jarvisx/src/App.tsx' }
 *   }))
 *
 * and the pane updates without prop drilling.
 */
export function FilePreviewPane({
  apiBaseUrl,
  projectRoot,
  open,
  onClose,
  previewPath,
}: Props) {
  const [content, setContent] = useState<string>('')
  const [size, setSize] = useState(0)
  const [truncated, setTruncated] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const baseUrl = apiBaseUrl.replace(/\/$/, '')

  const fetchFile = useCallback(
    async (path: string) => {
      if (!path) {
        setContent('')
        setError(null)
        setLoading(false)
        return
      }
      setLoading(true)
      setError(null)
      try {
        // Try project-rooted read first; fall back to workspace read for
        // workspace-rooted paths (MEMORY.md etc) where projectRoot might
        // not contain them.
        let url: string
        if (projectRoot) {
          url =
            `${baseUrl}/api/project/read?root=${encodeURIComponent(projectRoot)}` +
            `&path=${encodeURIComponent(path)}`
        } else {
          url = `${baseUrl}/api/workspace/read?path=${encodeURIComponent(path)}`
        }
        const res = await fetch(url)
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail || `HTTP ${res.status}`)
        }
        const j = await res.json()
        let text = String(j?.content ?? '')
        const sz = Number(j?.size_bytes ?? text.length)
        let trunc = !!j?.truncated
        // Defensive: enforce our own cap on top of backend's
        if (text.length > MAX_BYTES) {
          text = text.slice(0, MAX_BYTES)
          trunc = true
        }
        setContent(text)
        setSize(sz)
        setTruncated(trunc)
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e))
        setContent('')
      } finally {
        setLoading(false)
      }
    },
    [baseUrl, projectRoot],
  )

  useEffect(() => {
    if (open && previewPath) void fetchFile(previewPath)
  }, [open, previewPath, fetchFile])

  const handleCopy = () => {
    if (!content) return
    navigator.clipboard.writeText(content).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  if (!open) return null

  return (
    <aside className="flex w-[480px] min-w-[320px] max-w-[60vw] flex-shrink-0 flex-col border-l border-line bg-bg1">
      <header className="flex flex-shrink-0 items-center gap-2 border-b border-line px-3 py-2">
        <FileText size={12} className="flex-shrink-0 text-accent" />
        <span
          className="min-w-0 flex-1 truncate font-mono text-[11px] text-fg"
          title={previewPath || ''}
        >
          {previewPath || '(ingen fil valgt)'}
        </span>
        {previewPath && (
          <button
            onClick={handleCopy}
            title="Kopiér indhold"
            className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
          </button>
        )}
        <button
          onClick={onClose}
          title="Luk preview"
          className="flex h-6 w-6 items-center justify-center rounded text-fg3 hover:bg-bg2 hover:text-fg"
        >
          <X size={12} />
        </button>
      </header>

      {previewPath && (
        <div className="flex flex-shrink-0 items-center gap-3 border-b border-line/40 bg-bg1/40 px-3 py-1 font-mono text-[10px] text-fg3">
          <span>{langFor(previewPath)}</span>
          <span>·</span>
          <span>{formatBytes(size)}</span>
          {truncated && (
            <>
              <span>·</span>
              <span className="text-warn">truncated</span>
            </>
          )}
          {loading && <Loader2 size={10} className="ml-auto animate-spin" />}
        </div>
      )}

      <div className="flex-1 overflow-auto bg-bg0">
        {error && (
          <div className="m-3 flex items-start gap-2 rounded border border-danger/30 bg-danger/10 px-3 py-2 text-[11px] text-danger">
            <AlertCircle size={11} className="mt-0.5 flex-shrink-0" />
            <span className="font-mono">{error}</span>
          </div>
        )}
        {!error && !previewPath && (
          <div className="flex h-full items-center justify-center text-center text-[11px] text-fg3">
            <div className="px-6">
              <FileText size={24} className="mx-auto mb-2 opacity-30" />
              <div>Vælg en fil for at se den her</div>
              <div className="mt-1 text-fg3/70">
                Klik på en fil i tree-panelet eller send en{' '}
                <code className="font-mono">jarvisx:preview-file</code> event
              </div>
            </div>
          </div>
        )}
        {!error && previewPath && content && (
          <SyntaxHighlighter
            language={langFor(previewPath)}
            style={vscDarkPlus}
            showLineNumbers
            wrapLongLines={false}
            customStyle={{
              margin: 0,
              padding: '12px 14px',
              background: 'transparent',
              fontSize: '12px',
              lineHeight: '1.55',
            }}
            lineNumberStyle={{
              color: '#4e5262',
              fontSize: '10px',
              minWidth: '2.5em',
              paddingRight: '12px',
              userSelect: 'none',
            }}
          >
            {content}
          </SyntaxHighlighter>
        )}
        {!error && previewPath && !content && !loading && (
          <div className="px-4 py-6 text-[11px] italic text-fg3">
            (tom fil)
          </div>
        )}
      </div>
    </aside>
  )
}

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}
