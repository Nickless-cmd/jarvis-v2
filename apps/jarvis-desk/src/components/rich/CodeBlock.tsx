import { useEffect, useState } from 'react'
import { codeToHtml } from 'shiki'

/** Code-block med Shiki-highlighting (samme engine som VS Code). Falder tilbage
 *  til ren <pre> mens Shiki loader. Kopiér-knap kopierer RÅ kildetekst (ingen
 *  linjenumre). dangerouslySetInnerHTML er på Shiki's egen escapede output af
 *  kode-strengen — ikke model-leveret HTML — så det er ikke en XSS-vektor. */
export function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [html, setHtml] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    codeToHtml(code, { lang: lang || 'text', theme: 'github-dark' })
      .then((h) => { if (alive) setHtml(h) })
      .catch(() => { if (alive) setHtml(null) })
    return () => { alive = false }
  }, [code, lang])

  return (
    <div className="codeblock">
      <div className="codeblock-bar">
        <span className="codeblock-lang">{lang || 'text'}</span>
        <button type="button" aria-label="Kopiér" onClick={() => navigator.clipboard.writeText(code)}>
          Kopiér
        </button>
      </div>
      {html ? (
        <div dangerouslySetInnerHTML={{ __html: html }} />
      ) : (
        <pre><code>{code}</code></pre>
      )}
    </div>
  )
}
