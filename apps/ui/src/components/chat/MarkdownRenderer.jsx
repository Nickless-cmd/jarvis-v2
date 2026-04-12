import { useState, useEffect, useRef } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import { Copy, Check } from 'lucide-react'
import mermaid from 'mermaid'

mermaid.initialize({ startOnLoad: false, theme: 'dark' })

/**
 * Renders a mermaid fenced block as an inline SVG diagram.
 * - Single stable DOM node (no conditional unmount → no flicker)
 * - Skips render while streaming; renders exactly once when stream ends
 * - After async SVG insert, re-scrolls .transcript to bottom
 * - Click opens a fullscreen overlay for large diagrams
 */
function MermaidBlock({ code, streaming }) {
  const ref = useRef(null)
  const lastRendered = useRef(null)
  const [fullscreen, setFullscreen] = useState(false)

  useEffect(() => {
    if (streaming) return
    if (!ref.current) return
    if (lastRendered.current === code) return

    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        if (!ref.current) return
        ref.current.innerHTML = svg
        lastRendered.current = code
        const transcript = ref.current.closest('.transcript')
        if (transcript) transcript.scrollTop = transcript.scrollHeight
      })
      .catch(() => {
        if (ref.current) ref.current.textContent = code
      })
  }, [code, streaming])

  return (
    <>
      <div
        ref={ref}
        className={`mermaid-block${streaming ? ' mermaid-pending' : ''}`}
        onClick={() => !streaming && setFullscreen(true)}
        title={streaming ? undefined : 'Klik for at forstørre'}
      >
        {streaming && <span style={{ color: '#6e7681', fontSize: '12px' }}>mermaid diagram…</span>}
      </div>
      {fullscreen && (
        <div className="mermaid-overlay" onClick={() => setFullscreen(false)}>
          <div
            className="mermaid-overlay-inner"
            dangerouslySetInnerHTML={{ __html: ref.current?.innerHTML || '' }}
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
