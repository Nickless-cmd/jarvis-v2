import { memo } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { BlocksRenderer } from './BlocksRenderer'

/** Besked-række med locked boble-layout: bruger højre (boble), Jarvis venstre
 *  (avatar + tekst, ingen boble). Density videregives til rich-blocks.
 *
 *  memo: afsluttede beskeder har stabile props → re-renderer IKKE når
 *  StreamContext tikker (elapsed-timer hver 500ms). Det er det der gør lange
 *  samtaler tunge — uden memo highlighter hver CodeBlock forfra 2×/sekund. */
function MessageRowImpl({
  role,
  blocks,
  density,
  streaming,
}: {
  role: 'user' | 'assistant'
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
}) {
  if (role === 'user') {
    const text = blocks.map((b) => (b.type === 'text' ? b.text : '')).join('')
    return (
      <div className="msg-user-wrap">
        <div className="bubble">{text}</div>
      </div>
    )
  }
  return (
    <div className="msg-jarvis-wrap">
      <article className="msg-jarvis">
        <div className="avatar-jarvis">J</div>
        <div className="jarvis-body">
          <BlocksRenderer blocks={blocks} density={density} streaming={streaming} />
        </div>
      </article>
    </div>
  )
}

export const MessageRow = memo(MessageRowImpl)
