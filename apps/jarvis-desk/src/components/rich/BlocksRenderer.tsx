import { useState } from 'react'
import type { ContentBlock } from '../../lib/sseProtocol'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ToolCard } from './ToolCard'
import { ImageBlock } from './ImageBlock'

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
  return (
    <>
      {blocks.map((b, i) => (
        <BlockView key={i} block={b} density={density} streaming={streaming} />
      ))}
    </>
  )
}

function BlockView({
  block,
  density,
  streaming,
}: {
  block: ContentBlock
  density: 'compact' | 'full'
  streaming: boolean
}) {
  const [thinkingOpen, setThinkingOpen] = useState(false)
  switch (block.type) {
    case 'text':
      return <MarkdownRenderer text={block.text} streaming={streaming} />
    case 'tool_use':
      return <ToolCard block={block} density={density} />
    case 'image':
      return <ImageBlock src={block.src} alt={block.alt} />
    case 'thinking':
      return (
        <div className="thinking">
          <button type="button" onClick={() => setThinkingOpen((o) => !o)}>
            {thinkingOpen ? 'Skjul tanke' : 'tænkte…'}
          </button>
          {thinkingOpen && <MarkdownRenderer text={block.thinking} streaming={false} />}
        </div>
      )
    default:
      return null
  }
}
