/** ChatGPTs målte ord-opdeling. Bevar mellemrum i samme del som ordet. */
export const DIL_TEXT_STREAMING_PART_PATTERN = /\s*\S+\s*|\s+$/g

export type StreamingTextVariant = 'Neutral' | 'Disabled' | 'Normal' | 'Snappy'

export interface StreamingTextParameters {
  colorDelay: number
  duration: number
  timeOffsetBetweenParts: number
  opacityKeyframes: readonly number[]
  controlPoints: readonly [number, number, number, number]
}

/**
 * Parameternavnene følger DILStreamingText. Desk bruger Normal; de øvrige
 * varianter er navngivne, så en variant ikke ender som spredte magic numbers.
 */
export const STREAMING_TEXT_VARIANTS: Record<StreamingTextVariant, StreamingTextParameters> = {
  Neutral: {
    colorDelay: 90,
    duration: 220,
    timeOffsetBetweenParts: 34,
    opacityKeyframes: [0, 0.72, 1],
    controlPoints: [0.2, 0.75, 0.25, 1],
  },
  Disabled: {
    colorDelay: 0,
    duration: 0,
    timeOffsetBetweenParts: 0,
    opacityKeyframes: [1, 1, 1],
    controlPoints: [0, 0, 1, 1],
  },
  Normal: {
    colorDelay: 110,
    duration: 240,
    timeOffsetBetweenParts: 38,
    opacityKeyframes: [0, 0.72, 1],
    controlPoints: [0.2, 0.75, 0.25, 1],
  },
  Snappy: {
    colorDelay: 70,
    duration: 170,
    timeOffsetBetweenParts: 26,
    opacityKeyframes: [0, 0.82, 1],
    controlPoints: [0.16, 0.84, 0.22, 1],
  },
}

export const STREAMING_TAIL_WORD_LIMIT = 3

/**
 * Halens variant. Desk brugte `Normal` (240 ms) indtil 18/11-2026.
 *
 * Det sidste ords samlede landing er `duration + colorDelay + 2×
 * timeOffsetBetweenParts` (tredje ord har order 2, og farve-animationen
 * starter efter `colorDelay`). Målt i Chromium 18/11-2026 med de faktiske
 * CSS-variabler: `Normal` 426 ms, `Snappy` 292 ms — 134 ms kortere, 31 %.
 *
 * Valget står HER og ikke som et argument på hvert kald, så det kan vendes
 * med én linje — og så de tre øvrige varianter ikke er tal ingen kan bruge.
 */
export const STANDARD_VARIANT: StreamingTextVariant = 'Snappy'

/**
 * Sidste grænse som ender i whitespace. Det viste præfiks kan ende midt i et
 * ord; det ord er ikke afsluttet og må derfor ikke flytte animationshalen.
 */
export function afsluttetGraense(text: string): number {
  let boundary = 0
  DIL_TEXT_STREAMING_PART_PATTERN.lastIndex = 0
  for (const match of text.matchAll(DIL_TEXT_STREAMING_PART_PATTERN)) {
    if (/\s$/u.test(match[0])) boundary = (match.index ?? 0) + match[0].length
  }
  return boundary
}

type HastText = { type: 'text'; value: string }
type HastElement = {
  type: 'element'
  tagName: string
  properties?: Record<string, unknown>
  children: HastNode[]
}
type HastParent = { type: 'root'; children: HastNode[] } | HastElement
type HastNode = HastText | HastParent | { type: string; [key: string]: unknown }

interface WordPart {
  node: HastText
  start: number
  end: number
}

const EXCLUDED_TAGS = new Set(['code', 'pre', 'math', 'svg', 'style', 'script'])

function erParent(node: HastNode): node is HastParent {
  return (node.type === 'root' || node.type === 'element') && Array.isArray((node as HastParent).children)
}

/**
 * Rehype-transformen pakker kun de sidste tre afsluttede, synlige ord. Den
 * rører ikke kode/matematik og tilføjer ingen wrapper omkring resten af DOM'en.
 */
export function rehypeStreamingTextTail(options: { completedAtEnd: boolean; variant?: StreamingTextVariant }) {
  return (tree: HastNode) => {
    const parts: WordPart[] = []

    const collect = (node: HastNode, excluded: boolean) => {
      if (node.type === 'text') {
        const text = node as HastText
        if (!excluded && text.value) {
          DIL_TEXT_STREAMING_PART_PATTERN.lastIndex = 0
          for (const match of text.value.matchAll(DIL_TEXT_STREAMING_PART_PATTERN)) {
            if (/\S/u.test(match[0])) {
              const start = match.index ?? 0
              parts.push({ node: text, start, end: start + match[0].length })
            }
          }
        }
        return
      }
      if (!erParent(node)) return
      const nextExcluded = excluded || (node.type === 'element' && EXCLUDED_TAGS.has(node.tagName))
      for (const child of node.children) collect(child, nextExcluded)
    }
    collect(tree, false)

    // Hvis det viste præfiks ender midt i et ord, er sidste synlige AST-del
    // endnu ikke afsluttet. Halen vælges fra delene FØR den.
    const completedParts = options.completedAtEnd ? parts : parts.slice(0, -1)
    const selected = new Set(completedParts.slice(-STREAMING_TAIL_WORD_LIMIT))
    if (selected.size === 0) return
    const order = new Map([...selected].map((part, index) => [part, index]))
    const parameters = STREAMING_TEXT_VARIANTS[options.variant ?? STANDARD_VARIANT]
    const controlPoints = parameters.controlPoints.join(', ')

    const replace = (node: HastNode) => {
      if (!erParent(node)) return
      const children: HastNode[] = []
      for (const child of node.children) {
        if (child.type !== 'text') {
          replace(child)
          children.push(child)
          continue
        }
        const text = child as HastText
        const nodeParts = parts.filter((part) => part.node === text && selected.has(part))
        if (nodeParts.length === 0) {
          children.push(child)
          continue
        }
        let cursor = 0
        for (const part of nodeParts) {
          if (part.start > cursor) children.push({ type: 'text', value: text.value.slice(cursor, part.start) })
          children.push({
            type: 'element',
            tagName: 'jarvis-stream-word',
            properties: {
              className: ['streaming-word-tail'],
              'data-stream-part-key': `${parts.indexOf(part)}:${text.value.slice(part.start, part.end)}`,
              'data-stream-tail-order': order.get(part) ?? 0,
              style: [
                `--streaming-tail-order:${order.get(part) ?? 0}`,
                `--streaming-tail-duration:${parameters.duration}ms`,
                `--streaming-tail-color-delay:${parameters.colorDelay}ms`,
                `--streaming-tail-part-offset:${parameters.timeOffsetBetweenParts}ms`,
                `--streaming-tail-opacity-start:${parameters.opacityKeyframes[0] ?? 0}`,
                `--streaming-tail-opacity-mid:${parameters.opacityKeyframes[1] ?? 1}`,
                `--streaming-tail-opacity-end:${parameters.opacityKeyframes[2] ?? 1}`,
                `--streaming-tail-easing:cubic-bezier(${controlPoints})`,
              ].join(';'),
            },
            children: [{ type: 'text', value: text.value.slice(part.start, part.end) }],
          })
          cursor = part.end
        }
        if (cursor < text.value.length) children.push({ type: 'text', value: text.value.slice(cursor) })
      }
      node.children = children
    }
    replace(tree)
  }
}
