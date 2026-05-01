import { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'
import mermaid from 'mermaid'
import { InlineToolResult } from './InlineToolResult'

// Match a single line that introduces a tool_result reference:
//   [tool_result:tool-result-XXXXXXXXXXXXXXXX]
// followed (optionally) by one summary line like:
//   [edit_file]: Edited /path/to/file.py (1 replacement)
// We intercept the pair and replace with an expandable card that
// lazy-fetches the full result via /api/tool-result/{id}.
const TOOL_RESULT_LINE = /^\[tool_result:(tool-result-[a-f0-9]+)\]\s*$/
const TOOL_USE_HINT = /^Use read_tool_result with result_id="[^"]+" to inspect the full output\.\s*$/

/**
 * Splits a content string into segments — markdown text vs tool_result
 * blocks. Each tool_result block carries its result_id and optional
 * summary line for compact display.
 */
function splitToolResults(content) {
  if (!content) return [{ type: 'text', value: '' }]
  const lines = content.split('\n')
  const segments = []
  let buffer = []
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(TOOL_RESULT_LINE)
    if (!m) {
      buffer.push(lines[i])
      continue
    }
    // Flush text buffer
    if (buffer.length > 0) {
      segments.push({ type: 'text', value: buffer.join('\n') })
      buffer = []
    }
    const resultId = m[1]
    // The next line (if present) is usually the summary like "[edit_file]: ..."
    let summary = ''
    let consumed = 1
    if (i + 1 < lines.length && lines[i + 1].trim() && !TOOL_RESULT_LINE.test(lines[i + 1])) {
      summary = lines[i + 1]
      consumed = 2
    }
    // Skip the trailing "Use read_tool_result with result_id=..." hint line if any
    if (
      i + consumed < lines.length &&
      TOOL_USE_HINT.test(lines[i + consumed])
    ) {
      consumed += 1
    }
    segments.push({ type: 'tool_result', resultId, summary })
    i += consumed - 1
  }
  if (buffer.length > 0) {
    segments.push({ type: 'text', value: buffer.join('\n') })
  }
  return segments
}

mermaid.initialize({ startOnLoad: false, theme: 'dark' })

// Module-level cache: survives React StrictMode double-mount and component remounts.
// Key = diagram code string, value = animation-stripped SVG string.
const mermaidSvgCache = new Map()

function stripAnimations(svg) {
  return svg.replace(
    /(<style[^>]*>)/,
    '$1* { animation: none !important; transition: none !important; }'
  )
}

/**
 * Renders a mermaid fenced block as an inline SVG.
 * - Module-level cache: survives React StrictMode double-mount → no flicker
 * - Skips render while streaming
 * - Strips mermaid's looping animations from the SVG
 * - After SVG lands, re-scrolls .transcript to bottom
 * - Click opens a fullscreen overlay (uses data URI to avoid ID conflicts)
 */
function MermaidBlock({ code, streaming }) {
  const [svgString, setSvgString] = useState(() => mermaidSvgCache.get(code) ?? null)
  const [fullscreen, setFullscreen] = useState(false)
  const containerRef = useRef(null)

  useEffect(() => {
    if (streaming) return
    if (mermaidSvgCache.has(code)) {
      if (!svgString) setSvgString(mermaidSvgCache.get(code))
      return
    }

    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        const clean = stripAnimations(svg)
        mermaidSvgCache.set(code, clean)
        setSvgString(clean)
      })
      .catch(() => {
        mermaidSvgCache.set(code, null)
      })
  }, [code, streaming])

  useEffect(() => {
    if (!svgString || !containerRef.current || fullscreen) return
    const transcript = containerRef.current.closest('.transcript')
    if (!transcript) return
    const distanceFromBottom = transcript.scrollHeight - transcript.scrollTop - transcript.clientHeight
    if (distanceFromBottom < 120) transcript.scrollTop = transcript.scrollHeight
  }, [svgString, fullscreen])

  if (streaming || !svgString) {
    return (
      <div className="mermaid-block mermaid-pending">
        <span style={{ color: '#6e7681', fontSize: '12px' }}>mermaid diagram…</span>
      </div>
    )
  }

  return (
    <>
      <div
        ref={containerRef}
        className="mermaid-block"
        dangerouslySetInnerHTML={{ __html: svgString }}
        onClick={() => setFullscreen(true)}
        title="Klik for at forstørre"
        style={{ cursor: 'zoom-in' }}
      />
      {fullscreen && (
        <div className="mermaid-overlay" onClick={() => setFullscreen(false)}>
          <div
            className="mermaid-overlay-inner"
            dangerouslySetInnerHTML={{ __html: svgString }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}
    </>
  )
}

/**
 * Renders a syntax-highlighted code block with a floating copy button
 * and a 300px max-height with scroll for long blocks.
 */
function CodeBlock({ language, code }) {
  const [copied, setCopied] = useState(false)

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div style={{ position: 'relative' }}>
      <button onClick={handleCopy} className="code-copy-btn" title="Kopiér kode">
        {copied ? <Check size={13} /> : <Copy size={13} />}
      </button>
      <SyntaxHighlighter
        style={oneDark}
        language={language || 'text'}
        PreTag="div"
        customStyle={{
          margin: '0.5em 0',
          borderRadius: '6px',
          fontSize: '0.85em',
          maxHeight: '300px',
          overflowY: 'auto',
        }}
      >
        {code}
      </SyntaxHighlighter>
    </div>
  )
}

/**
 * Renders markdown content in chat bubbles.
 * Supports paragraphs, bold, italic, lists, links, tables (remark-gfm),
 * inline code, fenced code blocks with syntax highlighting,
 * copy button, 300px scroll cap, and mermaid diagram rendering.
 */
export function MarkdownRenderer({ content, streaming = false }) {
  if (!content) return null

  // Intercept tool_result blocks before passing to Markdown — render
  // each as an expandable InlineToolResult card with surrounding text
  // segments still flowing through Markdown.
  const segments = splitToolResults(content)
  if (segments.length > 1 || segments[0]?.type === 'tool_result') {
    return (
      <>
        {segments.map((seg, i) =>
          seg.type === 'tool_result' ? (
            <InlineToolResult
              key={`tr-${seg.resultId}-${i}`}
              resultId={seg.resultId}
              summary={seg.summary}
            />
          ) : seg.value ? (
            <MarkdownRendererInner
              key={`txt-${i}`}
              content={seg.value}
              streaming={streaming}
            />
          ) : null,
        )}
      </>
    )
  }

  return <MarkdownRendererInner content={content} streaming={streaming} />
}

function MarkdownRendererInner({ content, streaming }) {
  return (
    <Markdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Block-level code: <pre><code class="language-x">…</code></pre>
        pre({ children }) {
          const codeChild = children?.props
          if (!codeChild) return <pre>{children}</pre>

          const className = codeChild.className || ''
          const match = /language-(\w+)/.exec(className)
          const language = match ? match[1] : 'text'
          const codeText = String(codeChild.children || '').replace(/\n$/, '')

          if (language === 'mermaid') {
            return <MermaidBlock code={codeText} streaming={streaming} />
          }

          return <CodeBlock language={language} code={codeText} />
        },
        // Inline code: `backtick`
        code({ children, ...props }) {
          return (
            <code className="inline-code" {...props}>
              {children}
            </code>
          )
        },
        // Open links in new tab — show inline preview for /files/ images
        a({ children, href, ...props }) {
          const isFileImage = href && /\/files\/[^/]+\.(png|jpg|jpeg|gif|webp|svg|bmp)(\?|$)/i.test(href)
          return (
            <>
              <a href={href} target="_blank" rel="noopener noreferrer" {...props}>
                {children}
              </a>
              {isFileImage && (
                <div style={{ marginTop: '6px' }}>
                  <img
                    src={href}
                    alt={String(children)}
                    style={{
                      maxWidth: '320px',
                      maxHeight: '240px',
                      borderRadius: '6px',
                      border: '1px solid rgba(255,255,255,0.08)',
                      display: 'block',
                      cursor: 'zoom-in',
                    }}
                    onClick={() => window.open(href, '_blank')}
                  />
                </div>
              )}
            </>
          )
        },
      }}
    >
      {content}
    </Markdown>
  )
}
