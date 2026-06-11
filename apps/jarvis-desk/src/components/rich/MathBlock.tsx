import { useEffect, useState } from 'react'

/** KaTeX-matematik, lazy-loaded første gang. Ved parse-fejl falder den tilbage
 *  til rå latex-tekst. dangerouslySetInnerHTML er på KaTeX's egen output af
 *  latex-strengen (bibliotekets tilsigtede API), ikke model-HTML. */
export function MathBlock({ latex }: { latex: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    import('katex')
      .then(({ default: katex }) => {
        try {
          const h = katex.renderToString(latex, { throwOnError: true })
          if (alive) setHtml(h)
        } catch {
          if (alive) setFailed(true)
        }
      })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [latex])

  if (failed) return <code>{latex}</code>
  if (html) return <span dangerouslySetInnerHTML={{ __html: html }} />
  return <code>{latex}</code>
}
