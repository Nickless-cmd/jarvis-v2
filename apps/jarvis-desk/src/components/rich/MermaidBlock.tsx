import { useEffect, useState } from 'react'
import { CodeBlock } from './CodeBlock'

/** Mermaid-diagram, lazy-loaded. Ved parse-fejl falder den tilbage til en
 *  rå CodeBlock af kilden. dangerouslySetInnerHTML er på Mermaid's egen SVG-
 *  output af diagram-kilden (bibliotekets tilsigtede API), ikke model-HTML. */
export function MermaidBlock({ source }: { source: string }) {
  const [svg, setSvg] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let alive = true
    import('mermaid')
      .then(async ({ default: mermaid }) => {
        try {
          mermaid.initialize({ startOnLoad: false, theme: 'dark' })
          const { svg: rendered } = await mermaid.render('m' + Math.abs(hash(source)), source)
          if (alive) setSvg(rendered)
        } catch {
          if (alive) setFailed(true)
        }
      })
      .catch(() => { if (alive) setFailed(true) })
    return () => { alive = false }
  }, [source])

  if (failed) return <CodeBlock code={source} lang="mermaid" />
  if (svg) return <div dangerouslySetInnerHTML={{ __html: svg }} />
  return <CodeBlock code={source} lang="mermaid" />
}

function hash(s: string): number {
  let h = 0
  for (let i = 0; i < s.length; i++) h = ((h << 5) - h + s.charCodeAt(i)) | 0
  return h
}
