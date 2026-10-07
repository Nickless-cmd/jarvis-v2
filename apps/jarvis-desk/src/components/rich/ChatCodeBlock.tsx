import { memo, useCallback, useEffect, useRef, useState, type CSSProperties } from 'react'
import { Check, Copy } from 'lucide-react'
import { highlightChatCode, type ChatHighlight } from '../../lib/chatCodeHighlight'
import { skrivTilUdklipsholder } from '../../lib/udklipsholder'

/** 29/9-2026: den rå kode vises straks. Shiki loader asynkront, og en
 *  mislykket sprogindlæsning må aldrig skjule eller ændre kildeteksten.
 *
 *  1/10-2026 (Bjørn: «desk mangler copy ikon og bash/js/python tags»): chat-
 *  kodeblokken blev bygget til streaming (1e0de8517) og fik hverken
 *  sprog-tag eller kopiér-knap med fra panelernes CodeBlock. Kopiér-knappen
 *  er den vigtigste af de to — kode i en chat skal UD af chatten, og uden
 *  knappen skal man markere i en flade der ruller vandret.
 *
 *  Kopiér går gennem `skrivTilUdklipsholder`, ikke `navigator.clipboard`
 *  direkte: den falder tilbage til `execCommand` og kvitterer først når
 *  teksten FAKTISK nåede udklipsholderen (se lib/udklipsholder.ts). */
export const ChatCodeBlock = memo(function ChatCodeBlock({ code, lang, className }: {
  code: string
  lang: string
  className?: string
}) {
  const [highlighted, setHighlighted] = useState<ChatHighlight | null>(null)
  const [kopieret, setKopieret] = useState(false)
  const [fejl, setFejl] = useState(false)
  const pending = useRef<Promise<ChatHighlight | null>>(Promise.resolve(null))
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!lang || !code) return
    let alive = true
    const next = pending.current.then((previous) =>
      highlightChatCode(code, lang, previous).catch(() => null))
    pending.current = next
    next.then((result) => { if (alive) setHighlighted(result) })
    return () => { alive = false }
  }, [code, lang])

  // Timeren ryddes ved unmount: fjernes blokken mens kvitteringen står, ville
  // et setState ellers ramme en komponent der ikke er der længere.
  useEffect(() => () => { if (timer.current) clearTimeout(timer.current) }, [])

  const kopiér = useCallback(async () => {
    const ok = await skrivTilUdklipsholder(code)
    if (!ok) { setFejl(true); return }
    setFejl(false)
    setKopieret(true)
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => setKopieret(false), 1500)
  }, [code])

  const kode = highlighted?.code === code && highlighted.lang === lang
    ? (
      <pre className="shiki chat-shiki"><code>
        {highlighted.tokens.map((line, lineIndex) => (
          <span className="line" key={lineIndex}>
            {line.map((token, tokenIndex) => (
              <span key={tokenIndex} style={token.htmlStyle as CSSProperties}>{token.content}</span>
            ))}
            {lineIndex < highlighted.tokens.length - 1 ? '\n' : null}
          </span>
        ))}
      </code></pre>
    )
    : <pre><code className={className}>{code}</code></pre>

  return (
    <div className="codeblock chat-codeblock">
      <div className="codeblock-bar">
        <span className="codeblock-lang">{lang || 'text'}</span>
        <button
          type="button"
          className="chat-code-copy"
          aria-label={fejl ? 'Kunne ikke kopiere' : kopieret ? 'Kopieret' : 'Kopiér kode'}
          title={fejl ? 'Kunne ikke kopiere' : kopieret ? 'Kopieret' : 'Kopiér kode'}
          onClick={() => void kopiér()}
        >
          {fejl ? 'Kunne ikke kopiere' : kopieret ? <Check size={14} aria-hidden="true" /> : <Copy size={14} aria-hidden="true" />}
        </button>
      </div>
      {kode}
    </div>
  )
})
