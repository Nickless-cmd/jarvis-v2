import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkBreaks from 'remark-breaks'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { enforceStructure } from '../../lib/enforceStructure'
import { stripToolEchoes } from '../../lib/stripToolEchoes'
import { safeLinkHref } from '../../lib/sanitize'

/** Render markdown sikkert. INGEN rehype-raw → rå HTML renderes aldrig
 *  (XSS-guard mod fjendtligt tool-output). Links saniteres + åbnes eksternt.
 *
 *  Strukturel håndhævelse: enforceStructure() konverterer Jarvis' uvane
 *  (`**Header:**`-afsnit) til ægte markdown-headers FØR ReactMarkdown ser
 *  teksten. Det giver konsekvent layout uafhængigt af hans skrivestil.
 *
 *  Hard-breaks: remarkBreaks gør ÉT newline til <br>. Jarvis emitter ofte afsnit
 *  adskilt af enkelt-\n (ikke \n\n); uden dette kollapser CommonMark dem til ét
 *  løbende afsnit ("kastet ind"). Med remarkBreaks adskilles hver linje — samme
 *  adfærd som claude.ai/Slack/Discord — uafhængigt af hans spacing. */
export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
  const stabilized = streaming ? stabilizeStreamingMarkdown(text) : text
  const md = enforceStructure(stripToolEchoes(stabilized))
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm, remarkBreaks]}
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
