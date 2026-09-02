import { forwardRef, useImperativeHandle, useRef } from 'react'
import { FlatList, StyleSheet, View } from 'react-native'
import type { ContentBlock } from '../lib/sseProtocol'
import { denseBlocks } from '../lib/blockHelpers'
import type { ChatMessage } from '../lib/types'
import { tokens } from '../theme/tokens'
import { nextUserRow } from '../lib/messageNav'
import { MessageBubble } from './MessageBubble'
import { InlineToolGroup } from './InlineToolGroup'
import { ThinkingLabel } from './ThinkingLabel'
import { describeTool, describeToolResult } from '../lib/toolSummary'
import { countFromResult, type ToolItem } from '../lib/toolGroup'
import { hasOrdering, parseBlocks, threadBlocks } from '../lib/persistedBlocks'
import { ToolResultCard } from './ToolResultCard'

export interface MessageListHandle {
  jumpTop: () => void       // ældste besked
  jumpBottom: () => void    // nyeste besked
  jumpOlderUser: () => void // forrige bruger-besked (op i historik)
  jumpNewerUser: () => void // næste bruger-besked (ned mod nyeste)
  scrubTo: (fraction: number) => void // 0=nyeste, 1=ældste
}

interface MessageListProps {
  messages: ChatMessage[]
  blocks: ContentBlock[]
  /** Vis «Tænker» nederst i tråden mens Jarvis arbejder (ChatGPT-mønsteret). */
  thinking?: boolean
  /**
   * Ekstra plads i bunden mens tastaturet er fremme.
   *
   * Komponisten svæver og stiger med tastaturet — uden dette blev tråden
   * stående, og de nyeste linjer forsvandt bag den. Nu følger indholdet med op.
   */
  bottomInset?: number
  onResend?: (text: string) => void
  /** Kaldes ved scroll-aktivitet (bruges til at vise Save Rail mens man scroller). */
  onScrollActivity?: () => void
}

type Row =
  | { kind: 'msg'; key: string; message: ChatMessage; hideActions?: boolean }
  | { kind: 'tool'; key: string; content: string }
  | { kind: 'live-tool'; key: string; name: string; body: string; running: boolean }
  /** Én RUNDE værktøjsarbejde, foldet sammen til én linje. */
  | { kind: 'tool-group'; key: string; items: ToolItem[] }

/**
 * Fold sammenhængende værktøjsrækker sammen til én pr. runde.
 *
 * Codex-appen viser fortælling → ÉN linje → fortælling. Uden det her stablede
 * vi fire «Kører verify_file_contains…» oven på hinanden — samme information
 * fire gange, og tråden mistede sin ro. En tekstbesked afslutter runden.
 */
function groupToolRounds(rows: Row[]): Row[] {
  const out: Row[] = []
  let buf: Row[] = []
  const flush = () => {
    if (buf.length === 0) return
    const items: ToolItem[] = buf.map((r) =>
      r.kind === 'live-tool'
        ? { label: describeTool(r.name, r.body, r.running), running: r.running, tool: r.name }
        : {
            label: describeToolResult((r as { content: string }).content),
            running: false,
            tool: /\[([a-z_0-9]+)\]\s*:/i.exec((r as { content: string }).content)?.[1] ?? '',
            count: countFromResult((r as { content: string }).content)
          }
    )
    out.push({ kind: 'tool-group', key: `group-${buf[0]!.key}`, items })
    buf = []
  }
  for (const r of rows) {
    if (r.kind === 'tool' || r.kind === 'live-tool') buf.push(r)
    else {
      flush()
      out.push(r)
    }
  }
  flush()
  return out
}

function toolBody(block: Extract<ContentBlock, { type: 'tool_use' }>): string {
  if (block.partialJson) return block.partialJson
  try {
    return Object.keys(block.input ?? {}).length ? JSON.stringify(block.input, null, 2) : ''
  } catch {
    return ''
  }
}

/**
 * Bygger streaming-rækker af de live blocks: tekst/thinking samles til
 * tekstbobler, og tool_use-blokke renderes som live tool-kort (fix: tidligere
 * blev tool-blokke filtreret væk under streaming → resultater dukkede først op
 * efter app-genstart fra persisterede beskeder).
 */
function buildStreamingRows(blocks: ContentBlock[]): Row[] {
  const rows: Row[] = []
  let textBuf = ''
  let i = 0
  const flush = () => {
    if (textBuf.trim()) {
      rows.push({
        kind: 'msg',
        key: `stream-text-${i}`,
        message: {
          id: `stream-text-${i}`,
          role: 'assistant',
          content: textBuf,
          created_at: new Date().toISOString()
        }
      })
      textBuf = ''
    }
    i += 1
  }
  // denseBlocks: `blocks` kan være sparsomt (foldede tool_result-content-blokke
  // efterlader `undefined`-huller mellem indices). `for..of` over det rå array
  // ville ramme et hul og crashe på `b.type` → hele React-træet unmounter → sort
  // skærm. `b &&` er defense-in-depth.
  for (const b of denseBlocks(blocks)) {
    if (!b) continue
    if (b.type === 'text') textBuf += b.text
    else if (b.type === 'thinking') textBuf += b.thinking
    else if (b.type === 'tool_use') {
      flush()
      rows.push({
        kind: 'live-tool',
        key: `stream-tool-${b.id || i}`,
        name: b.name,
        body: toolBody(b),
        running: b.status !== 'done' && b.status !== 'error'
      })
    }
  }
  flush()
  return rows
}

export const MessageList = forwardRef<MessageListHandle, MessageListProps>(function MessageList(
  { messages, blocks, onResend, onScrollActivity, thinking, bottomInset = 0 },
  ref
) {
  const flatRef = useRef<FlatList>(null)
  const visibleRef = useRef(0)   // ordered-index øverst i viewport (inverted)
  const contentLenRef = useRef(0)
  // Stabil callback — RN kaster hvis onViewableItemsChanged ændrer identitet on-the-fly.
  const onViewable = useRef(({ viewableItems }: { viewableItems: Array<{ index: number | null }> }) => {
    const first = viewableItems[0]
    if (first && first.index != null) visibleRef.current = first.index
  }).current

  /**
   * Har en gemt assistent-tur strukturerede blokke MED rækkefølge, bruges de
   * frem for den flade `content`. Ellers ville skærmen stadig vise den gamle
   * klump — værktøjer først, alle synteser smeltet sammen — selv om serveren
   * nu gemmer den rigtige orden.
   *
   * De løse `tool`-beskeder i samme tur er de SAMME resultater; de springes
   * over, så de ikke tælles to gange.
   */
  const persisted: Row[] = []
  let skipToolRows = false
  for (let i = messages.length - 1; i >= 0; i--) {
    const m = messages[i]!
    if (m.role === 'assistant') {
      const blocks = parseBlocks(m)
      if (hasOrdering(blocks)) {
        const expanded: Row[] = []
        const thread = threadBlocks(blocks!)
        const lastTextIdx = thread.reduce(
          (acc, b, i) => (b.type === 'text' && (b.text ?? '').trim() ? i : acc),
          -1
        )
        thread.forEach((b, bi) => {
          if (b.type === 'text' && (b.text ?? '').trim()) {
            expanded.push({
              kind: 'msg',
              key: `${m.id}-b${bi}`,
              message: { ...m, id: `${m.id}-b${bi}`, content: (b.text ?? '').trim() },
              // Kun turens sidste afsnit bærer kopiér/oplæs — ellers gentages
              // rækken efter hvert afsnit og tråden bliver støjende.
              hideActions: bi !== lastTextIdx
            })
          } else if (b.type === 'tool_use') {
            expanded.push({
              kind: 'live-tool',
              key: `${m.id}-t${bi}`,
              name: String(b.name ?? ''),
              body: JSON.stringify(b.input ?? {}),
              running: false
            })
          }
        })
        persisted.unshift(...expanded)
        skipToolRows = true
        continue
      }
      skipToolRows = false
    }
    if (m.role === 'user') skipToolRows = false
    if (m.role === 'tool') {
      if (skipToolRows) continue
      persisted.unshift({ kind: 'tool', key: m.id, content: m.content })
      continue
    }
    persisted.unshift({ kind: 'msg', key: m.id, message: m })
  }

  const rows: Row[] = groupToolRounds([...persisted, ...buildStreamingRows(blocks)])

  // Inverteret liste: nyeste række sidder altid i bunden og er synlig fra start.
  const ordered = [...rows].reverse()
  // I inverted liste: HØJERE index = ÆLDRE besked, LAVERE index = NYERE.
  const userFlags = ordered.map((r) => r.kind === 'msg' && r.message.role === 'user')

  useImperativeHandle(ref, () => ({
    jumpTop: () => flatRef.current?.scrollToEnd({ animated: true }),
    jumpBottom: () => flatRef.current?.scrollToOffset({ offset: 0, animated: true }),
    jumpOlderUser: () => {
      const i = nextUserRow(userFlags, visibleRef.current, 1)
      if (i != null) flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0 })
    },
    jumpNewerUser: () => {
      const i = nextUserRow(userFlags, visibleRef.current, -1)
      if (i != null) flatRef.current?.scrollToIndex({ index: i, animated: true, viewPosition: 0 })
    },
    scrubTo: (f: number) => flatRef.current?.scrollToOffset({ offset: f * contentLenRef.current, animated: false }),
  }), [userFlags])

  return (
    <FlatList
      ref={flatRef}
      inverted
      // Inverteret liste: ListHeaderComponent tegnes NEDERST på skærmen —
      // altså lige efter den nyeste besked, præcis hvor ChatGPT viser
      // «Thinking». Det er derfor labelen ligger her og ikke over komponisten.
      ListHeaderComponent={thinking ? <ThinkingLabelRow /> : null}
      data={ordered}
      keyExtractor={(item) => item.key}
      onContentSizeChange={(_w, h) => { contentLenRef.current = h }}
      onScroll={onScrollActivity ? () => onScrollActivity() : undefined}
      scrollEventThrottle={120}
      onViewableItemsChanged={onViewable}
      onScrollToIndexFailed={(info) => {
        flatRef.current?.scrollToOffset({ offset: info.averageItemLength * info.index, animated: true })
      }}
      renderItem={({ item }) => {
        // Værktøjsarbejde er ÉN linje inde i samtalen — ikke et kort.
        // Målt i Codex-tråden: «</> Ændrede 16 filer ›». Det fulde output
        // ligger bag linjen, ikke foran den.
        if (item.kind === 'tool-group') return <InlineToolGroup items={item.items} />
        return (
          <MessageBubble
            message={item.message}
            onResend={item.message.role === 'user' ? onResend : undefined}
            hideActions={item.hideActions}
          />
        )
      }}
      // INVERTERET: paddingTop lander visuelt NEDERST — det er dér tastaturet
      // og komponisten æder plads.
      contentContainerStyle={[styles.content, { paddingTop: BOTTOM_CLEARANCE + bottomInset }]}
      keyboardShouldPersistTaps="handled"
    />
  )
})

function ThinkingLabelRow() {
  return (
    <View style={styles.thinkingRow}>
      <ThinkingLabel />
    </View>
  )
}

/**
 * INVERTERET liste: indholdet er vendt 180°, så contentContainer'ens
 * `paddingTop` lander VISUELT NEDERST og `paddingBottom` visuelt øverst.
 * Det er kontraintuitivt nok til at være værd at skrive ned.
 *
 * Tallene er plads til de to svævende bjælker. Bunden er 124 og ikke bare
 * komponistens egen højde: handlingsrækken (kopiér/læs op) hænger UNDER
 * turens sidste afsnit, og med for lidt luft gled netop de to ikoner ind bag
 * komponisten. Man skal måle til bunden af det SIDSTE element, ikke af teksten.
 */
const BOTTOM_CLEARANCE = 124
const TOP_CLEARANCE = 72

const styles = StyleSheet.create({
  thinkingRow: { paddingHorizontal: tokens.spacing.lg },
  content: {
    // paddingTop sættes dynamisk (BOTTOM_CLEARANCE + tastaturhøjde) — se
    // contentContainerStyle. Kun den øverste er konstant.
    paddingBottom: TOP_CLEARANCE
  }
})
