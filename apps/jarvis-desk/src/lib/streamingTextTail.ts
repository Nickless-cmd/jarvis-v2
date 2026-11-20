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
    colorDelay: 360,
    duration: 800,
    timeOffsetBetweenParts: 60,
    opacityKeyframes: [0, 0.18, 0.72, 1],
    controlPoints: [0.25, 0.1, 0.25, 1],
  },
  Disabled: {
    colorDelay: 0,
    duration: 0,
    timeOffsetBetweenParts: 0,
    opacityKeyframes: [1, 1, 1, 1],
    controlPoints: [0, 0, 1, 1],
  },
  Normal: {
    colorDelay: 315,
    duration: 700,
    timeOffsetBetweenParts: 35,
    opacityKeyframes: [0, 0.18, 0.72, 1],
    controlPoints: [0.25, 0.1, 0.25, 1],
  },
  Snappy: {
    colorDelay: 99,
    duration: 220,
    timeOffsetBetweenParts: 30,
    opacityKeyframes: [0, 0.18, 0.72, 1],
    controlPoints: [0.25, 0.1, 0.25, 1],
  },
}

export const STREAMING_TAIL_WORD_LIMIT = 3

/**
 * Halens variant. Desk brugte `Normal` (240 ms) indtil 18/11-2026.
 *
 * Tallene er GPT-appens egne, laest ud af `/opt/codex-desktop/resources/
 * app.asar` 20/11-2026 (`dil_text/src/rendering/DILStreamingText`). Der er
 * fire saet: `Neutral` og `Normal` deler skabelonen `s`, `Snappy` er `c`
 * (= `s` med kortere tid), og `Disabled` er nul. GPT vaelger `Snappy` naar
 * `snappyStreamingAnimations` er slaaet til, ellers `Normal`.
 *
 * Det sidste ords samlede landing er `duration + colorDelay + 2×
 * timeOffsetBetweenParts` (tredje ord har order 2, og farve-animationen
 * starter efter `colorDelay`). Med GPT's snappy-tal: 220 + 99 + 60 = 379 ms.
 * Den tidligere maaling i Chromium (18/11-2026) gav 292 ms for et saet tal
 * der ikke var GPT's — derfor er de erstattet.
 *
 * Valget står HER og ikke som et argument på hvert kald, så det kan vendes
 * med én linje — og så de tre øvrige varianter ikke er tal ingen kan bruge.
 */
export const STANDARD_VARIANT: StreamingTextVariant = 'Snappy'

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
export function rehypeStreamingTextTail(options: { variant?: StreamingTextVariant } = {}) {
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

    if (parts.length === 0) return
    // ALLE synlige ord pakkes — også det sidste, som under SSE ofte er midt i
    // et ord. Det er netop det ord brugeren ser blive skrevet, så det skal
    // farves nu, ikke først når næste token ankommer.
    //
    // Målt 20/11-2026 i Chromium: med `parts.slice(0, -1)` var der ALTID ét
    // ord mindre pakket end der var ord i teksten — «ord1 … ord6» gav fem
    // spans — så det nyeste ord stod gråt indtil det næste kom. Bjørns ord:
    // «det sidste ord bliver aldrig blåt». `StreamingWord` genbruger sin node
    // og læser teksten fra live props, så et ord der vokser bliver opdateret
    // uden at animationen starter forfra — derfor er der intet at beskytte.
    const completedParts = parts
    // ALLE afsluttede ord pakkes ind — kun de sidste tre bærer animationsklassen.
    // Grunden er React-nøglerne: react-markdown nøgler børn `<tagName>-<antal>`,
    // så med kun tre wrappers rykkede hvert nyt ord alle positioner ét ned, og
    // hver wrapper blev genmonteret → hvert ord animerede op til 3 gange
    // (MÅLT i Chromium 20/11-2026). Når hvert ord har sin egen stabile position,
    // genbruger React dets node, og animationen kører præcis én gang.
    const selected = new Set(completedParts.slice(-STREAMING_TAIL_WORD_LIMIT))
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
        const nodeParts = parts.filter((part) => part.node === text)
        if (nodeParts.length === 0) {
          children.push(child)
          continue
        }
        let cursor = 0
        for (const part of nodeParts) {
          if (part.start > cursor) children.push({ type: 'text', value: text.value.slice(cursor, part.start) })
          const inTail = selected.has(part)
          children.push({
            type: 'element',
            tagName: 'jarvis-stream-word',
            properties: {
              className: [inTail ? 'streaming-word-tail' : 'streaming-word-settled'],
              // Nøglen bærer ordets POSITION først, så en måling kan skelne et
              // ord der vokser («o» → «or» → «ord1») fra et ord der genstarter.
              // Den ligger på begge grene: et ord der endnu ikke er i halen skal
              // også kunne identificeres.
              'data-stream-part-key': `${parts.indexOf(part)}:${text.value.slice(part.start, part.end)}`,
              ...(inTail
                ? {
                    'data-stream-tail-order': order.get(part) ?? 0,
                    style: [
                      `--streaming-tail-order:${order.get(part) ?? 0}`,
                      `--streaming-tail-duration:${parameters.duration}ms`,
                      `--streaming-tail-color-delay:${parameters.colorDelay}ms`,
                      `--streaming-tail-part-offset:${parameters.timeOffsetBetweenParts}ms`,
                      `--streaming-tail-opacity-start:${parameters.opacityKeyframes[0] ?? 0}`,
                      `--streaming-tail-opacity-early:${parameters.opacityKeyframes[1] ?? 0.18}`,
                      `--streaming-tail-opacity-mid:${parameters.opacityKeyframes[2] ?? 0.72}`,
                      `--streaming-tail-opacity-end:${parameters.opacityKeyframes[3] ?? 1}`,
                      `--streaming-tail-easing:cubic-bezier(${controlPoints})`,
                    ].join(';'),
                  }
                : {}),
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
