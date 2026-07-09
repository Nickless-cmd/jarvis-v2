import type { ContentBlock } from '../../lib/sseProtocol'
import { denseBlocks } from '../../lib/blockHelpers'
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
  // denseBlocks: fjern sparsomme huller (foldede tool_result-indices) FØR render —
  // ellers crasher enhver iteration der tilgår b.type på et undefined-hul (sort skærm).
  const dense = denseBlocks(blocks)
  const lastIdx = dense.length - 1
  return (
    <>
      {dense.map((b, i) => (
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
  switch (block.type) {
    case 'text':
      return <MarkdownRenderer text={block.text} streaming={streaming} />
    case 'tool_use':
      return <ToolCard block={block} density={density} />
    case 'image':
      return <ImageBlock src={block.src} alt={block.alt} />
    case 'thinking': {
      // "Live" = han tænker lige NU (sidste blok + streamer stadig) → vis
      // "tænker…" + den ægte thinking-content mens den strømmer.
      const live = streaming && isLast
      // FORBI-tænkning skjules. Den sammenfoldede "tænkte…"-chip var legacy fra
      // FØR vi havde ægte thinking-content — en hardcoded label der bare stod
      // tilbage som rod mellem tool-kald og i færdige beskeder (Bjørn 2026-06-13).
      // Den ægte thinking-content forsvinder som den skal; labelen skal også væk.
      if (!live) return null
      return (
        <div className="thinking live">
          <LiveVerb text="tænker" />
          <MarkdownRenderer text={block.thinking} streaming />
        </div>
      )
    }
    default:
      return null
  }
}
