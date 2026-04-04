import Markdown from 'react-markdown'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'

/**
 * Renders markdown content in chat bubbles.
 * Supports paragraphs, bold, italic, lists, links, inline code, and fenced code blocks
 * with syntax highlighting.
 *
 * react-markdown v10 no longer passes an `inline` prop to code components.
 * Instead we override `pre` to handle block-level code (fenced blocks) and
 * let the `code` component handle only inline code (`backtick`).
 */
export function MarkdownRenderer({ content }) {
  if (!content) return null

  return (
    <Markdown
      components={{
        // Block-level code: <pre><code class="language-x">…</code></pre>
        pre({ children }) {
          // children is typically a single <code> element rendered by react-markdown
          const codeChild = children?.props
          if (!codeChild) return <pre>{children}</pre>

          const className = codeChild.className || ''
          const match = /language-(\w+)/.exec(className)
          const codeText = String(codeChild.children || '').replace(/\n$/, '')

          return (
            <SyntaxHighlighter
              style={oneDark}
              language={match ? match[1] : 'text'}
              PreTag="div"
              customStyle={{
                margin: '0.5em 0',
                borderRadius: '6px',
                fontSize: '0.85em',
              }}
            >
              {codeText}
            </SyntaxHighlighter>
          )
        },
        // Inline code: `backtick` — rendered as simple <code>
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
