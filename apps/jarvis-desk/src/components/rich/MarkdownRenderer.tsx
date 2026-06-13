import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { enforceStructure } from '../../lib/enforceStructure'
import { stripToolEchoes } from '../../lib/stripToolEchoes'
import { safeLinkHref } from '../../lib/sanitize'

/** Render markdown sikkert. INGEN rehype-raw → rå HTML renderes aldrig
 *  (XSS-guard mod fjendtligt tool-output). Links saniteres + åbnes eksternt.
 *
 *  Strukturel håndhævelse: enforceStructure() konverterer Jarvis' uvaner
 *  (`**Header:**`-afsnit, inline `## Header` midt i en linje) til ægte
 *  markdown-blokke FØR ReactMarkdown ser teksten. Det giver konsekvent layout.
 *
 *  remarkBreaks FJERNET (2026-06-13): den gjorde ÉT newline til <br>, hvilket
 *  forstærkede HVER parse-fejl (især malformede tabeller) til en <br>-jammet
 *  mur = "kastet ind". GLM emitterer korrekte blanklinjer, og backend-
 *  normalizeren (markdown_structure) + enforceStructure genskaber struktur for
 *  de sjældne 0-newline-tilfælde — så remarkBreaks er nu overflødig og skadelig.
 *  (Den var et band-aid mod deepseeks single-\n-afsnit; rod-årsagen løses
 *  server-side i stedet.) */
export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
  const stabilized = streaming ? stabilizeStreamingMarkdown(text) : text
  const md = enforceStructure(stripToolEchoes(stabilized))
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
