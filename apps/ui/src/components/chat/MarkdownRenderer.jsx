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
 * Skips rendering while streaming (code changes every token → flicker).
 * After rendering, scrolls the nearest .transcript to bottom so the
 * async SVG insert doesn't leave content hidden behind the composer.
 * Falls back to raw code text on render errors.
 */
function MermaidBlock({ code, streaming }) {
  const ref = useRef(null)
  const lastRendered = useRef(null)

  useEffect(() => {
    if (streaming) return          // wait until stream is done
    if (!ref.current) return
    if (lastRendered.current === code) return  // already rendered this exact code

    const id = `mermaid-${Math.random().toString(36).slice(2)}`
    mermaid
      .render(id, code)
      .then(({ svg }) => {
        if (!ref.current) return
        ref.current.innerHTML = svg
        lastRendered.current = code
        // Re-scroll transcript after async SVG insert
        const transcript = ref.current.closest('.transcript')
        if (transcript) transcript.scrollTop = transcript.scrollHeight
      })
      .catch(() => {
        if (ref.current) ref.current.textContent = code
      })
  }, [code, streaming])

  if (streaming) {
    return (
      <div className="mermaid-block mermaid-pending">
        <span style={{ color: '#6e7681', fontSize: '12px' }}>mermaid diagram…</span>
      </div>
    )
  }

  return <div ref={ref} className="mermaid-block" />
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
