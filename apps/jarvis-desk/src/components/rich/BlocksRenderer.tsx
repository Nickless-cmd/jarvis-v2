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
      // "Live" = han tænker lige nu (sidste blok + streamer stadig) → folder
      // automatisk ud, siger "tænker…".
      const live = streaming && isLast
      // 2026-06-13: forbi-tænkning skjules IKKE længere. Før returnerede vi null
      // for ikke-live blokke, så hver rundes tænkning forsvandt når næste runde
      // kom — Bjørn nåede ikke at læse dem. Nu bliver de som sammenfoldede
      // "tænkte…"-chips man kan klikke op og læse bagefter.
      const open = userToggled !== null ? userToggled : live
      return (
        <div className={`thinking ${live ? 'live' : 'past'}`}>
          <button type="button" onClick={() => setUserToggled(!open)}>
            <LiveVerb text={live ? 'tænker' : 'tænkte'} />
          </button>
          {open && <MarkdownRenderer text={block.thinking} streaming={live} />}
        </div>
      )
    }
    default:
      return null
  }
}
