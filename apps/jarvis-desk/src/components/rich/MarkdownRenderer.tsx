import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { safeLinkHref } from '../../lib/sanitize'

/** Render markdown sikkert. INGEN rehype-raw → rå HTML renderes aldrig
 *  (XSS-guard mod fjendtligt tool-output). Links saniteres + åbnes eksternt. */
export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
  const md = streaming ? stabilizeStreamingMarkdown(text) : text
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        a: ({ href, children }) => {
          const safe = href ? safeLinkHref(href) : null
          if (!safe) return <span>{children}</span>
          return (
            <a
              href={safe}
              rel="noopener noreferrer"
              onClick={(e) => {
                e.preventDefault()
                openExternal(safe)
              }}
            >
              {children}
            </a>
          )
        },
      }}
    >
      {md}
    </ReactMarkdown>
  )
}

function openExternal(url: string): void {
  const w = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => void } }).jarvisDesk
  if (w?.openExternal) w.openExternal(url)
}
