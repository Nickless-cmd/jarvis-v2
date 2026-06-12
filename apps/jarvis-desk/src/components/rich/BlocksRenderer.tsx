import { useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ToolCard } from './ToolCard'
import { ImageBlock } from './ImageBlock'
import { LiveVerb } from '../shell/LiveVerb'

/** Dispatcher content-blocks til de rette rich-komponenter. Density-aware:
 *  videregives til ToolCard (compact|full). */
export function BlocksRenderer({
  blocks,
  density,
  streaming,
}: {
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
}) {
  const lastIdx = blocks.length - 1
  return (
    <>
      {blocks.map((b, i) => (
        <BlockView key={i} block={b} density={density} streaming={streaming} isLast={i === lastIdx} />
      ))}
    </>
  )
}

function BlockView({
  block,
  density,
  streaming,
  isLast,
}: {
  block: ContentBlock
  density: 'compact' | 'full'
  streaming: boolean
  isLast: boolean
}) {
  // null = følg auto-tilstanden (live); true/false = brugeren har selv foldet.
  const [userToggled, setUserToggled] = useState<boolean | null>(null)
  switch (block.type) {
    case 'text':
      return <MarkdownRenderer text={block.text} streaming={streaming} />
    case 'tool_use':
      return <ToolCard block={block} density={density} />
    case 'image':
      return <ImageBlock src={block.src} alt={block.alt} />
    case 'thinking': {
      // "Live" = han tænker lige nu: denne thinking-blok er den sidste OG vi
      // streamer stadig. Så folder feltet automatisk ud og siger "tænker…".
      // Når svaret begynder (thinking er ikke længere sidste blok), folder det
      // sig sammen til "tænkte…". Brugeren kan altid override manuelt.
      const live = streaming && isLast
      // Live-tænkning vises mens han tænker. De gemte/forbi "tænkte…"-blokke
      // mellem tool-kald er redundante nu (live-tænkning dækker dem) → skjul dem.
      if (!live) return null
      const open = userToggled !== null ? userToggled : true
      return (
        <div className="thinking live">
          <button type="button" onClick={() => setUserToggled(!open)}>
            <LiveVerb text="tænker" />
          </button>
          {open && <MarkdownRenderer text={block.thinking} streaming />}
        </div>
      )
    }
    default:
      return null
  }
}
