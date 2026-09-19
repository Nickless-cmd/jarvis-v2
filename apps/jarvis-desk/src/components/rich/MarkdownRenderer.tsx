import { memo, useMemo } from 'react'
import ReactMarkdown, { type Components } from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { stabilizeStreamingMarkdown } from '../../lib/streamingMarkdown'
import { enforceStructure } from '../../lib/enforceStructure'
import { stripToolEchoes } from '../../lib/stripToolEchoes'
import { delIBlokke } from '../../lib/markdownBlokke'
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
// Stabile referencer: et nyt `components`-objekt eller plugin-array ved hver
// render ville få react-markdown til at bygge alt om, også uændrede blokke.
const PLUGINS = [remarkGfm]
const KOMPONENTER: Components = {
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
}

/** Én blok markdown. Memoiseret på strengen: en færdig blok parses én gang. */
export const MarkdownBlok = memo(function MarkdownBlok({ md }: { md: string }) {
  return <ReactMarkdown remarkPlugins={PLUGINS} components={KOMPONENTER}>{md}</ReactMarkdown>
})

export function MarkdownRenderer({ text, streaming }: { text: string; streaming: boolean }) {
  const md = useMemo(() => {
    const stabilized = streaming ? stabilizeStreamingMarkdown(text) : text
    return enforceStructure(stripToolEchoes(stabilized))
  }, [text, streaming])
  // Under streaming: blokke, så kun den sidste (levende) parses ved hver
  // delta (lib/markdownBlokke). Færdig tekst: ét samlet parse — det er den
  // endelige gengivelse, og blokdelingen skal aldrig kunne ændre den.
  const blokke = useMemo(() => (streaming ? delIBlokke(md) : null), [md, streaming])
  if (!blokke) return <MarkdownBlok md={md} />
  return (
    <>
      {blokke.map((b, i) => <MarkdownBlok key={i} md={b} />)}
    </>
  )
}

function openExternal(url: string): void {
  const w = (window as unknown as { jarvisDesk?: { openExternal?: (u: string) => void } }).jarvisDesk
  if (w?.openExternal) w.openExternal(url)
}
