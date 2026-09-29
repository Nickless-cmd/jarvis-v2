import { memo, useEffect, useRef, useState, type CSSProperties } from 'react'
import { highlightChatCode, type ChatHighlight } from '../../lib/chatCodeHighlight'

/** 29/9-2026: den rå kode vises straks. Shiki loader asynkront, og en
 *  mislykket sprogindlæsning må aldrig skjule eller ændre kildeteksten. */
export const ChatCodeBlock = memo(function ChatCodeBlock({ code, lang, className }: {
  code: string
  lang: string
  className?: string
}) {
  const [highlighted, setHighlighted] = useState<ChatHighlight | null>(null)
  const pending = useRef<Promise<ChatHighlight | null>>(Promise.resolve(null))

  useEffect(() => {
    if (!lang || !code) return
    let alive = true
    const next = pending.current.then((previous) =>
      highlightChatCode(code, lang, previous).catch(() => null))
    pending.current = next
    next.then((result) => { if (alive) setHighlighted(result) })
    return () => { alive = false }
  }, [code, lang])

  if (highlighted?.code !== code || highlighted.lang !== lang) {
    return <pre><code className={className}>{code}</code></pre>
  }

  return (
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
})
