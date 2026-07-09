import type { ContentBlock } from '../../lib/sseProtocol'
import { groupReadSearch, type RenderBlock } from '../../lib/groupReadSearch'
import { MarkdownRenderer } from './MarkdownRenderer'
import { ToolCard } from './ToolCard'
import { ToolGroupCard } from './ToolGroupCard'
import { ImageBlock } from './ImageBlock'
import { ProgressTrail } from './ProgressTrail'
import { LiveVerb } from '../shell/LiveVerb'

type ProgressBlock = Extract<ContentBlock, { type: 'progress' }>

/** Saml sammenhængende progress-blokke til ét ProgressTrail-element; alt andet
 *  passeres uændret. Ren transform (view-lokal) — persist/wire urørt. */
type ProgressTrailBlock = { type: 'progress_trail'; items: ProgressBlock[] }

function coalesceProgress(blocks: RenderBlock[]): (RenderBlock | ProgressTrailBlock)[] {
  const out: (RenderBlock | ProgressTrailBlock)[] = []
  let run: ProgressBlock[] = []
  const flush = () => {
    if (run.length > 0) {
      out.push({ type: 'progress_trail', items: run })
      run = []
    }
  }
  for (const b of blocks) {
    if (b.type === 'progress') {
      run.push(b as ProgressBlock)
    } else {
      flush()
      out.push(b)
    }
  }
  flush()
  return out
}

/** Dispatcher content-blocks til de rette rich-komponenter. Density-aware:
 *  videregives til ToolCard (compact|full).
 *
 *  Ren render-lags-transform: groupReadSearch folder ≥3 sammenhængende read/søge-
 *  tool_use-blokke til ét foldbart tool_group-kort. Ingen wire/persist-ændring —
 *  transformen kører her, efter fold, lige før dispatch. */
export function BlocksRenderer({
  blocks,
  density,
  streaming,
}: {
  blocks: ContentBlock[]
  density: 'compact' | 'full'
  streaming: boolean
}) {
  const rendered = coalesceProgress(groupReadSearch(blocks))
  const lastIdx = rendered.length - 1
  return (
    <>
      {rendered.map((b, i) => (
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
  block: RenderBlock | ProgressTrailBlock
  density: 'compact' | 'full'
  streaming: boolean
  isLast: boolean
}) {
  switch (block.type) {
    case 'progress_trail':
      return <ProgressTrail items={block.items} />
    case 'progress':
      // Enkelt progress-blok (skulle være coalesced, men vær robust).
      return <ProgressTrail items={[block]} />
    case 'text':
      return <MarkdownRenderer text={block.text} streaming={streaming} />
    case 'tool_group':
      return <ToolGroupCard block={block} density={density} />
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
