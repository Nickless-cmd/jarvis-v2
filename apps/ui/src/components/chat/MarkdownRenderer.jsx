import { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'
import mermaid from 'mermaid'

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
    if (!svgString || !containerRef.current) return
    const transcript = containerRef.current.closest('.transcript')
    if (transcript) transcript.scrollTop = transcript.scrollHeight
  }, [svgString])

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
        // Open links in new tab
        a({ children, ...props }) {
          return (
            <a target="_blank" rel="noopener noreferrer" {...props}>
              {children}
            </a>
          )
        },
      }}
    >
      {content}
    </Markdown>
  )
}
