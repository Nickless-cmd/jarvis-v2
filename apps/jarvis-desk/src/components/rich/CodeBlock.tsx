import { useEffect, useState } from 'react'
import { codeToHtml } from 'shiki'
import { skrivTilUdklipsholder } from '../../lib/udklipsholder'

/** Code-block med Shiki-highlighting (samme engine som VS Code). Falder tilbage
 *  til ren <pre> mens Shiki loader. Kopiér-knap kopierer RÅ kildetekst (ingen
 *  linjenumre). dangerouslySetInnerHTML er på Shiki's egen escapede output af
 *  kode-strengen — ikke model-leveret HTML — så det er ikke en XSS-vektor.
 *
 *  1/10-2026: kopiér gik gennem `navigator.clipboard.writeText` direkte —
 *  præcis den vej der blev afvist i den PAKKEDE app 18/9 (Electrons
 *  permission-handler svarede nej til `clipboard-sanitized-write`). Den gik
 *  fri i dev og fejlede i produktion. Nu bruger den `skrivTilUdklipsholder`,
 *  som har execCommand-faldbakken og kvitterer ærligt. */
export function CodeBlock({ code, lang }: { code: string; lang: string }) {
  const [html, setHtml] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    // 29/9-2026: samme lyse/mørke Shiki-tema som diff og chat-kode.
    codeToHtml(code, {
      lang: lang || 'text',
      themes: { light: 'github-light', dark: 'github-dark' },
      defaultColor: false,
    })
      .then((h) => { if (alive) setHtml(h) })
      .catch(() => { if (alive) setHtml(null) })
    return () => { alive = false }
  }, [code, lang])

  return (
    <div className="codeblock">
      <div className="codeblock-bar">
        <span className="codeblock-lang">{lang || 'text'}</span>
        <button type="button" aria-label="Kopiér" onClick={() => void skrivTilUdklipsholder(code)}>
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
